# make_me_scream
# 🔊 ScreamCPU
Plays warning sounds when your CPU reaches specific temperatures.

## ⚡ Quick Install
1. Install system deps: `sudo apt install mpv lm-sensors python3-pip`
2. Clone & install Python deps: 

pip install --user -r requirements.txt


Install & start user service (replace YOUR_USER with your username):
```bash
mkdir -p ~/.config/systemd/user
ln -s ~/screamcpu/screamcpu@.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now screamcpu@YOUR_USER.service

```
