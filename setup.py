#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Setup script for SAM.gov Crawler
This script helps you set up the environment and database for the SAM.gov crawler.
"""

import sys
import subprocess
import os
import platform


def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 6):
        print("Error: Python 3.6 or higher is required")
        sys.exit(1)
    print(f"✅ Python version: {sys.version.split()[0]}")


def install_requirements():
    """Install required packages."""
    requirements = [
        'scrapy',
        'pymysql',
        'openpyxl',  # Keep for backward compatibility
        'cryptography'  # Required for PyMySQL
    ]

    print("Installing required packages...")
    for package in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✅ Installed {package}")
        except subprocess.CalledProcessError:
            print(f"❌ Failed to install {package}")
            sys.exit(1)


def setup_mysql():
    """Help user set up MySQL."""
    print("\nMySQL Database Setup Instructions:")
    print("=================================")
    print("1. Make sure MySQL server is installed and running")
    print("2. Create a database named 'sam_gov_data' (or you can specify a different name in the app)")
    print("3. Update the database configuration in settings.py or use the Database Config button in the GUI")

    if platform.system() == "Windows":
        print("\nInstalling MySQL on Windows:")
        print("1. Download MySQL installer from https://dev.mysql.com/downloads/installer/")
        print("2. Run the installer and follow the setup wizard")
        print("3. Make sure to remember the root password you set during installation")
    elif platform.system() == "Darwin":  # macOS
        print("\nInstalling MySQL on macOS:")
        print("1. Using Homebrew: brew install mysql")
        print("2. Start MySQL: brew services start mysql")
        print("3. Set root password: mysql_secure_installation")
    elif platform.system() == "Linux":
        print("\nInstalling MySQL on Linux (Ubuntu/Debian):")
        print("1. sudo apt update")
        print("2. sudo apt install mysql-server")
        print("3. sudo mysql_secure_installation")

    print("\nCreating the database:")
    print("mysql -u root -p")
    print("CREATE DATABASE sam_gov_data;")
    print("EXIT;")


def create_directories():
    """Create necessary directories."""
    dirs = ['crawler/spiders']
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    print("✅ Created necessary directories")


def print_usage_instructions():
    """Print usage instructions."""
    print("\nUsage Instructions:")
    print("=================")
    print("1. Run the GUI application:")
    print("   python entrypoint.py")
    print("\n2. Configure the database connection using the 'Database Config' button")
    print("\n3. Set your search parameters and click one of the crawler buttons")
    print("\n4. Data will be stored in your MySQL database in the 'sam_opportunities' table")


def main():
    """Main function."""
    print("SAM.gov Crawler Setup")
    print("====================")

    check_python_version()
    install_requirements()
    create_directories()
    setup_mysql()
    print_usage_instructions()

    print("\nSetup completed successfully!")


if __name__ == "__main__":
    main()