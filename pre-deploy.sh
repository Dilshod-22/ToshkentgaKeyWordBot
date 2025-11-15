#!/bin/bash
# Rust o'rnatish
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Virtual environment yaratish va aktivlash
python3.12 -m venv .venv
source .venv/bin/activate

# Pip va paketlarni yangilash
pip install --upgrade pip setuptools wheel

# Requirements o'rnatish
pip install -r requirements.txt
