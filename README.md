
# Terneo Climate Integration for Home Assistant

This integration allows Home Assistant users to control and monitor Terneo thermostats.

## Features

- Control HVAC modes (Heat/Off).
- Monitor and set target temperatures.
- View the current temperature of the device.
- Supports multiple devices under one account.

## Installation

### ~~HACS (Home Assistant Community Store)~~ (coming soon)

~~1. Open HACS > Integrations > Explore & Add Repositories
2. Search for "Terneo Climate Integration".
3. Install the integration.~~

### Manual

1. Clone or download this repository.
2. Copy the `terneo` folder to your `custom_components` folder in your Home Assistant configuration directory.
3. Restart Home Assistant.

## Configuration

After installation:

1. Navigate to Configuration > Integrations in the Home Assistant UI.
2. Click on the "+" button to add a new integration.
3. Search for "Terneo Climate" and select it.
4. Provide your Terneo account credentials.
5. Upon successful authentication, your Terneo devices will be added to Home Assistant.

## Troubleshooting

If you encounter issues:

1. Ensure all Terneo devices are online and accessible via the official Terneo app.
2. Check the Home Assistant logs for any error messages related to the Terneo integration.
3. Ensure each device has a unique serial number.

## Contributing

Contributions are welcome! Please submit pull requests against the `dev` branch.

## Disclaimer

This integration is not affiliated with or endorsed by Terneo. Use at your own risk.
