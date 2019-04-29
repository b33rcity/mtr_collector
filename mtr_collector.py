#!/usr/bin/env python3

import time
import ssl
import asyncio

"""
Collect test results and send them off when appropriate.
"""
class Collector:

    def __init__(self):
        self.tests = {}


    # Key test results to a tuple consisting of the target and a timestamp 
    # rounded down to the nearest 5th minute.
    def collect(self, test_data):
        test_time = time.strftime("%Y%m%d%H") + self.round_to_5th_min(
                                                    time.strftime("%M"))
        new_key = (test_data.splitlines()[1], test_time)
        if new_key in self.tests:
            self.tests[new_key].append(test_data)
            self.tests[new_key][0].cancel()
            self.tests[new_key][0] = asyncio.create_task(
                                        self.send_after_time(new_key, 1))
        else:
            self.tests.update({new_key: [asyncio.create_task(
                              self.send_after_time(new_key, 1)), test_data]})


    # Wait for <timeout> minutes (suggest 5), then dispatch the test results and 
    # delete the data. 
    async def send_after_time(self, tup_key, timeout):
        # TODO change the 5 back to 60 when not testing
        await asyncio.sleep(timeout * 5)
        # TODO change print() to a method that dumps to slack/email/file
        print(self.tests[tup_key])
        del self.tests[tup_key]


    # Fudge timestamps to capture MTRs that are offset by up to 5 minutes, but
    # test the same target. Side effect: should also prevent separate 
    # notificafions for the same target if the target is flapping. 
    @staticmethod
    def round_to_5th_min(numeric_string):
        if int(numeric_string[-1]) < 5:
            return numeric_string[0:-1] + "0"
        else:
            return numeric_string[0:-1] + "5"


async def catch_incoming(reader, writer):
    print(writer.get_extra_info('sockname'))
    data = await reader.read()
    writer.close()
    collector.collect(data.decode())


async def main():
    server = await asyncio.start_server(catch_incoming, "127.0.0.1", "22123",
                                        ssl=x509)

    async with server:
        await server.serve_forever()


x509 = ssl.SSLContext()
x509.load_cert_chain("./cert.pem", keyfile="./key.pem")
collector = Collector()

asyncio.run(main())
