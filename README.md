# NVMe plugin for Munin

Simple plugin for displaying useful info about installed nvme drives.

## Requirements
- Python 3.6
- [nvme-cli](https://github.com/linux-nvme/nvme-cli)

## Installation
1. Download this repo (or just the main file), then link `munin_nvme.py` to munin plugins directory:
```
ln -s /path/to/your/munin_nvme.py /etc/munin/plugins/nvme
```
Alternatively, you can just rename `munin_nvme.py` to `nvme` and drop it to `/etc/munin/plugins`.

2. Add these lines to `/etc/munin/plugin-conf.d/munin-node`:
```
[nvme]
user root
```

3. Restart munin-node. For Ubuntu: `service munin-node restart`.

## License
The MIT License (MIT). Please see [License File](LICENSE) for more information.
