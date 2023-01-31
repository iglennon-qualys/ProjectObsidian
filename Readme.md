# Generate Cloud Agent lists for migration

## Configuration File
The configuration file is a json format file which defines source and target activation keys and target 
proxy details.

### Format                     
```
{
    "proxy_details": "<Proxy Address/FQDN>",
    "source": {
        "api_url": "<Qualys API URL>",
        "keys": {
            "<Activiation Key Name>": "<Activiation Key ID>",
            "<Activiation Key Name>": "<Activiation Key ID>"
        }
    },    
    "target": {
        "api_url": "<Qualys API URL>",
        "keys": {
            "<Activiation Key Name>": "<Activiation Key ID>",
            "<Activiation Key Name>": "<Activiation Key ID>"
        }
    },
    "activiation_key_map": {
        "<Source Key Name>": "<Target Key Name>",
        "<Source Key Name>": "<Target Key Name>"
    }
}
```
