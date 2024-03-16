# HomeServer Tibber (14464)
Gira Homeserver 4 Logicmodule to fetch the actual and forecasted power prices per hour from tibber electricity provider to start / stop your power consuming devices when electricity is cheap / expensive.

## Developer Notes

Developed for the GIRA HomeServer 4.12! Won't work before due SSL certificate issues between HS and Tibber API.
Licensed under the LGPL to keep all copies & forks free!

:exclamation: **If you fork this project and distribute the module by your own CHANGE the Logikbaustein-ID because 14464 is only for this one and registered to @SvenBunge !!** :exclamation:

If something doesn't work like expected: Just open an issue. Even better: Fix the issue and fill a pull request.

## Installation

Download a [release](https://github.com/SvenBunge/hs_tibberprices/releases) and install the module / Logikbaustein like others in Experte.
You find the module in the category "Datenaustausch". Just pic the IP address, port and unit-id of your inverter and wire the output to your communication objects. 

The latest version of the module is also available in the [KNX-User Forum Download Section](https://service.knx-user-forum.de/?comm=download&id=14464)

## Documentation

This module fetches values via modbus TCP.

More [detailed documentation](doc/log14464.md)

For further questions use the [Forum](https://knx-user-forum.de/) of the KNX User Forum (German)

## Build from scratch

1. Download [Schnittstelleninformation](http://www.hs-help.net/hshelp/gira/other_documentation/Schnittstelleninformationen.zip) from GIRA Homepage
2. Decompress zip, use `HSL SDK/2-0/framework` Folder for development.
3. Checkout this repo to the `projects/hs_tibberprices` folder
4. Run the generator.pyc (`python2 ./generator.pyc hs_tibberprices`)
5. Import the module `release/14464_hs_tibberprices.hsl` into the Experte Software
6. Use the module in your logic editor

You can replace step 4 with the `./buildRelease.sh` script. With the help of the markdown2 python module (`pip install markdown2`) it creates the documentation and packages the `.hslz` file. This file is also installable in step 5 and adds the module documentation into the Experte-Tool.  
 
## Libraries

* enum34
* six
* websocket

The shipped libraries may distributed under a different license conditions. Respect those licenses as well!
