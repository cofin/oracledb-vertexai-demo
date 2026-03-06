#!/bin/bash
set -e

# Detect architecture
ARCH=$(uname -m)
ORACLE_HOME="/opt/oracle"
mkdir -p "$ORACLE_HOME"

if [ "$ARCH" = "x86_64" ]; then
    echo "Detected x86_64 architecture."
    URL="https://download.oracle.com/otn_software/linux/instantclient/2340000/instantclient-basiclite-linux.x64-23.4.0.24.05.zip"
    DIR_NAME="instantclient_23_4"
elif [ "$ARCH" = "aarch64" ]; then
    echo "Detected aarch64 architecture."
    URL="https://download.oracle.com/otn_software/linux/instantclient/1919000/instantclient-basiclite-linux.arm64-19.19.0.0.0dbru.zip"
    DIR_NAME="instantclient_19_19"
else
    echo "Unsupported architecture: $ARCH"
    exit 1
fi

echo "Downloading Oracle Instant Client from $URL..."
curl -L -o /tmp/instantclient.zip "$URL"

echo "Unzipping..."
unzip /tmp/instantclient.zip -d "$ORACLE_HOME"
rm /tmp/instantclient.zip

if [ -d "$ORACLE_HOME/$DIR_NAME" ]; then
    echo "Oracle Client installed to $ORACLE_HOME/$DIR_NAME"
    ln -s "$ORACLE_HOME/$DIR_NAME" "$ORACLE_HOME/instantclient"
    echo "Symlinked to $ORACLE_HOME/instantclient"

    # Cleanup unnecessary files to save space
    cd "$ORACLE_HOME/instantclient"
    rm -f *jdbc* *occi* *mysql* *README *jar uidrvci genezi adrci
    echo "Cleaned up unnecessary files."

    # Setup TNS Admin
    mkdir -p "$ORACLE_HOME/instantclient/network/admin"
    echo "export LD_LIBRARY_PATH=$ORACLE_HOME/instantclient:\$LD_LIBRARY_PATH" > /etc/profile.d/oracle.sh
else
    echo "Error: Directory $ORACLE_HOME/$DIR_NAME not found after unzip."
    ls -la "$ORACLE_HOME"
    exit 1
fi
