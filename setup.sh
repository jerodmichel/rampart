#!/bin/bash
# installer

# create directories
mkdir -p ~/.local/share/rampart
mkdir -p ~/.local/bin

# copy all files
cp -r * ~/.local/share/rampart/

# install launcher
cp bin/rampart ~/.local/bin/

# Set permissions
chmod +x ~/.local/bin/rampart

echo "Installed! Run with: rampart"
