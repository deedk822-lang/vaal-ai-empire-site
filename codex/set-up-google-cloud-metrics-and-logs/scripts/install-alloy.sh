#!/bin/bash
# Install Grafana Alloy for Vaal AI Empire
# Supports Ubuntu/Debian, CentOS/RHEL, and macOS

set -e

ALLOY_VERSION="1.3.0"
INSTALL_DIR="/usr/local/bin"
SERVICE_USER="alloy"
SERVICE_GROUP="alloy"
CONFIG_DIR="/etc/alloy"
LOG_DIR="/var/log/alloy"

echo "=== Installing Grafana Alloy v${ALLOY_VERSION} ==="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    else
        echo "Cannot detect OS"
        exit 1
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

echo "Detected OS: $OS"

# Create user and group
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "Creating $SERVICE_USER user..."
    sudo useradd --system --no-create-home --shell /bin/false "$SERVICE_USER"
fi

# Create directories
echo "Creating directories..."
sudo mkdir -p "$CONFIG_DIR" "$LOG_DIR"
sudo chown "$SERVICE_USER:$SERVICE_GROUP" "$LOG_DIR"

# Download and install based on OS
if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
    echo "Installing for Debian/Ubuntu..."
    
    # Add Grafana repository
    sudo apt-get update
    sudo apt-get install -y apt-transport-https software-properties-common wget
    
    wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
    echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
    
    sudo apt-get update
    sudo apt-get install -y alloy
    
elif [[ "$OS" == "centos" || "$OS" == "rhel" || "$OS" == "fedora" ]]; then
    echo "Installing for RHEL/CentOS/Fedora..."
    
    # Add Grafana repository
    sudo tee /etc/yum.repos.d/grafana.repo <<EOF
[grafana]
name=grafana
baseurl=https://packages.grafana.com/oss/rpm
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://packages.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
EOF
    
    sudo yum install -y alloy
    
elif [[ "$OS" == "macos" ]]; then
    echo "Installing for macOS..."
    
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Please install Homebrew first."
        exit 1
    fi
    
    brew install grafana-alloy
else
    # Fallback to binary installation
    echo "Installing from binary..."
    
    ARCH=$(uname -m)
    if [[ "$ARCH" == "x86_64" ]]; then
        ARCH="amd64"
    elif [[ "$ARCH" == "aarch64" ]]; then
        ARCH="arm64"
    fi
    
    DOWNLOAD_URL="https://github.com/grafana/alloy/releases/download/v${ALLOY_VERSION}/alloy-linux-${ARCH}.zip"
    
    echo "Downloading from $DOWNLOAD_URL"
    wget -q "$DOWNLOAD_URL" -O /tmp/alloy.zip
    unzip -o /tmp/alloy.zip -d /tmp/
    sudo mv /tmp/alloy-linux-${ARCH} "$INSTALL_DIR/alloy"
    sudo chmod +x "$INSTALL_DIR/alloy"
fi

# Verify installation
echo "Verifying installation..."
if command -v alloy &> /dev/null; then
    alloy --version
else
    echo "Alloy not found in PATH"
    exit 1
fi

# Create systemd service (Linux only)
if [[ "$OS" != "macos" ]]; then
    echo "Creating systemd service..."
    
    sudo tee /etc/systemd/system/alloy.service <<EOF
[Unit]
Description=Grafana Alloy
Documentation=https://grafana.com/docs/alloy
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$CONFIG_DIR
EnvironmentFile=-/etc/default/alloy
ExecStart=/usr/bin/alloy run --storage.path=/var/lib/alloy/data $CONFIG_DIR/config.alloy
Restart=always
RestartSec=5

# Security settings
NoNewPrivileges=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=$LOG_DIR /var/lib/alloy/data

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    echo "Systemd service created. Use: sudo systemctl start alloy"
fi

# Create default config directory
echo "Setting up configuration directory..."
sudo mkdir -p "$CONFIG_DIR"
sudo chown "$SERVICE_USER:$SERVICE_GROUP" "$CONFIG_DIR"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Copy your Alloy config to: $CONFIG_DIR/config.alloy"
echo "2. Set environment variables in: /etc/default/alloy"
echo "3. Start the service: sudo systemctl start alloy"
echo "4. Check status: sudo systemctl status alloy"
echo ""
echo "Configuration directory: $CONFIG_DIR"
echo "Log directory: $LOG_DIR"
