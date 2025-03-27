#!/bin/bash
# encoding: utf-8
# Copyright (c) 2024- SATURN
# AUTHORS
# Sukbong Kwon (Galois)

venv=s2tlive
force=false


CUR_DIR=$(pwd)

# Set python virtual environment
if [ -d ~/pyenv/${venv} ]; then
    echo "'${venv}' python virtual environment exists."
    if $force; then
        echo "force mode"
        source ~/pyenv/${venv}/bin/activate
        pip uninstall -y -r <(pip freeze)
        python -m pip install --upgrade pip
    fi
else
    echo "Installing '${venv}' python virtual environment."
    cd ~/pyenv
    python -m venv ${venv} --without-pip
    source ~/pyenv/${venv}/bin/activate
    curl https://bootstrap.pypa.io/get-pip.py | python
    deactivate
    cd ${CUR_DIR}
fi

# Activate python virtual environment & upgrade pip
source ~/pyenv/${venv}/bin/activate
python -m pip install --upgrade pip

# Install requriements
echo "Installing requirements..."
pip install -r requirements.txt
echo "Done."
