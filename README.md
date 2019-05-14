# mtr_collector

This is a simple "server" for putting MTRs from multiple sources together into a single collection of data, as an intermediate step between the MTR being run and the MTR being posted to some notification channel. 

This was made with monitoring solutions like Icinga2 or Nagios in mind. Specifically, this is meant to be a piece of an Event Handler which runs an MTR from the monitoring server to the monitored host when it detects a failure. Even more specifically, this is meant for the particular case of having a *cluster* of monitoring servers which might be monitoring the same host from multiple locations. In this edge case, it's very possible for large clusters to overwhelm a channel in Discord or Slack, or fill your email inbox with "useless" noise; this script should mitigate the noisiness without losing the data.

## Set up

Installation is pretty easy:
1. Install Python 3.7
2. Install `pip` for Python 3.7
3. Install `pipenv` with pip
4. `chmod +x install.sh`
5. `./install.sh`
6. Put your settings into `collector.toml`
7. `systemctl --user start mtr_collector`

## Usage

Refer to clientspec.txt for detailed info on how to send data to the server. A very simple example client can be found in helpers.sh (the function `send_crted`, specifically). 

More "fully featured" client implementations are an exercise for the reader. 

Email note: Gmail will consider this an "insecure" app and will demand you explicitly enable the use of such apps before this script can use your gmail account for sending out MTRs. That's entirely up to you, but a better option might be to roll your own exim or postfix instance on the same machine, use '127.0.0.1' in the conf file, and then make a very strict firewall. (Just be sure to force the mail server to only talk to gmail on IPv4 if you have a dual-stack connection; gmail is extremely picky about IPv6.)
