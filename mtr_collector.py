#!/usr/bin/env python3

import os
import ssl
import toml
import time
import asyncio
import smtplib
import logging
import inspect
import os.path
import urllib.parse
import urllib.request
from datetime import timedelta
from email.message import EmailMessage

"""
Initialization
"""
os.chdir(os.path.dirname(inspect.getframeinfo(inspect.currentframe()).filename))
logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"), format='%(asctime)s %(message)s')

"""
Gather up needed config settings
"""
# Parse the conf file
with open("./collector.toml") as cfg:
    conf = toml.loads(cfg.read())

# Webhook settings
webhook_url = conf["webhook"]["url"]
webhook_headers = conf["webhook"]["headers"]
if "Authorization" in webhook_headers.keys() and conf["webhook"]["key"]:
    webhook_headers["Authorization"] = webhook_headers["Authorization"].format(conf["webhook"]["key"])

# TLS settings
x509 = ssl.SSLContext()
x509.load_cert_chain(conf["tls"]["cert"], keyfile=conf["tls"]["key"])
x509.load_verify_locations(cafile=conf["tls"]["cacrt"])
x509.verify_mode = ssl.CERT_REQUIRED

# Server settings
listen_ip = conf["collector"]["ip"]
listen_port = conf["collector"]["port"]

# Email settings
mail_from = conf["mail"]["from"]
mail_to = conf["mail"]["to"]
try:
    smtp_user, smtp_pw = tuple(conf["mail"]["smtp_login"].split(","))
except KeyError:
    logging.warning("No SMTP credentials given! If this is incorrect,"
          " please set smtp_login in collector.toml")
smtp = conf["mail"]["server"]


"""
Run the server until the process is killed
"""
async def main():
    server = await asyncio.start_server(catch_incoming, listen_ip, listen_port,
                                        ssl=x509)
    logging.info(f"Starting Collector (bound to {listen_ip}:{listen_port})")
    async with server:
        await server.serve_forever()


async def catch_incoming(reader, writer):
    client = writer.get_extra_info('peername')[0] + ":" + str(writer.get_extra_info('peername')[1])
    logging.info(f"Handling connection from {client}")
    data = await reader.read()
    writer.close()
    collect(data.decode())


"""
Collect test results into a dictionary and schedule their being sent.
Automatically clean up any that are 30 minutes old.
"""
tests = {}
def collect(test_data):
    test_time = timedelta(seconds=time.time()) # Server's time
    metadata = test_data.splitlines()[:4] # 0: monitor, 1: target, 2: monitor's time, 3: method
    key = metadata[1]
    notice_method = metadata[3] # One of: webhook, email, finish. Sent by client.
    logging.info(f" ... updating queue: '{notice_method}' for {key}")
    if key in tests:
        test = tests[key]
        test["tests"].append({
                 "monitor": metadata[0],
                 "mtr": test_data.splitlines()[4:],
        })
        test["monitors"].append(metadata[0])
        test["task"].cancel()
        test["timeout"].cancel()
        test["task"] = asyncio.create_task(send_after_time(test, 2, notice_method))
        test["timeout"] = asyncio.create_task(send_after_time(test, 30, "finish"))
    else:
        tests.update({
            key: {
                "time": test_time,
                "target": metadata[1],
                "monitors": [metadata[0]],
                "tests": [{ "monitor": metadata[0],
                            "mtr": test_data.splitlines()[4:] }],
            }
        })
        tests[key]["task"] = asyncio.create_task(send_after_time(tests[key], 2,
                                                                 notice_method))
        tests[key]["timeout"] = asyncio.create_task(send_after_time(tests[key], 30,
                                                                    "finish"))


"""
Send a collection of tests using the client-specified method after the timeout
period has finished. Original settings: 2 minutes to send, 30 minutes to
automatic removal.
"""
async def send_after_time(test, timeout, method):
    await asyncio.sleep(timeout * 60) # sleep takes int as seconds
    results = ''
    for t in test["tests"]:
        results += f'From {t["monitor"]}:'
        results += '\n'.join(t["mtr"])
        results += "\n"
    monitors = test["monitors"]
    target = test["target"]
    if method == "webhook":
        response = send_by_webhook(monitors, target, results)
    elif method == "email":
        response = send_by_email(monitors, target, results)
    elif method == "finish":
        logging.info(f"'finish' method called on {target}")
        response = "Removed test data"
        test["timeout"].cancel()
        del tests[target]
    logging.info(response)


"""
Transmission handlers
"""
def send_by_webhook(monitors, target, results):
    webhook = urllib.request.Request(webhook_url, headers=webhook_headers)
    dconf = conf["webhook"]["data"]
    if "intro" in dconf["body"].keys():
        body = dconf["body"]["intro"].format_map(tests[target]) + results
    else:
        body = results
    if "close" in dconf["body"].keys():
        body = body + dconf["body"]["close"]
    content = {dconf["channels"]["label"]: dconf["channels"]["list"], dconf["body"]["label"]: body}
    opt = conf["webhook"]["options"]
    for k in opt:
        if isinstance(opt[k], str):
            opt[k] = opt[k].format_map(tests[target])
        content.update({k: opt[k]})
    webhook.data = bytes(urllib.parse.urlencode(content), 'utf-8')
    logging.info("Sending to webhook....")
    try:
        response = urllib.request.urlopen(webhook)
    except HTTPError as e:
        return f"Error sending to webhook: {e.reason}"
    else:
        return "Successfully sent to webhook."


def send_by_email(monitors, target, results):
    msg = EmailMessage()
    msg.set_content(results)
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = f'MTRs to {target}'
    logging.info("Sending to email....")
    with smtplib.SMTP_SSL(smtp, context=x509) as srv:
        if smtp_pw:
            try:
                srv.login(smtp_user, smtp_pw)
            except Exception as e:
                return f"{type(e)}  -- Please double check your SMTP server settings!"
        response = srv.send_message(msg)
        return f"Email sent!\n(problem recipients: {len(response.keys())} - {response})"


if __name__ == "__main__":
    asyncio.run(main())
