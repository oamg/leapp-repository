#!/bin/sh

/usr/bin/journalctl --system -S '1 month ago' | /usr/bin/grep -q -m1 -w sctp
