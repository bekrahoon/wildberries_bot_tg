# Telegram-Bot for Wildberries Sales Analytics

## Table of Contents

- [Telegram-Bot for Wildberries Sales Analytics](#telegram-bot-for-wildberries-sales-analytics)
  - [Table of Contents](#table-of-contents)
  - [Description](#description)
  - [Features](#features)
  - [Installation](#installation)
  - [Usage](#usage)
  - [File Structure](#file-structure)
  - [Example Commands](#example-commands)
    - [Add a Shop](#add-a-shop)
    - [Delete a Shop](#delete-a-shop)
    - [List Shops](#list-shops)
    - [Generate a Report](#generate-a-report)
  - [Dependencies](#dependencies)
  - [Error Handling](#error-handling)
  - [Logging](#logging)
  - [Contributing](#contributing)


## Description
This is a Telegram bot designed to provide analytics for Wildberries stores. The bot allows users to manage multiple stores, retrieve sales reports for specified periods, and display key performance indicators in an easy-to-read format.

## Features
- **Support for Multiple Stores**: Manage data for multiple Wildberries stores using unique API keys.
- **Add Shop (/addshop)**:
  - Request the API key.
  - Optionally validate the API key using Wildberries API.
  - Request and save the shop name for easier identification.
- **Delete Shop (/delshop)**:
  - Remove a store by name with user confirmation.
- **List Shops (/shops)**:
  - Display all saved shops and their names.
- **Generate Sales Report (/report)**:
  - Select a shop (if multiple are available) using inline buttons.
  - Specify a reporting period (e.g., today, yesterday, last 7 days, or custom dates).
  - Retrieve and calculate sales data, including:
    - Total sales amount
    - Wildberries commission
    - Discounts applied
    - Acquiring commission
    - Logistics cost
    - Storage cost
    - Additional metrics (e.g., units sold, average selling price)
  - Format the report with Markdown for readability.
- **Help (/help)**:
  - Display information about available commands.

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/bekrahoon/wildberries_bot_tg.git
   cd wildberries_bot_tg
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables:**
   - Create a `.env` file based on `.env.example`.
   - Fill in the required variables (e.g., `TELEGRAM_BOT_TOKEN`).

## Usage

1. **Run the bot:**
   ```bash
   python bot.py
   ```

2. **Interact with the bot via Telegram:**
   - Use `/addshop` to add a new store.
   - Use `/delshop` to delete a store.
   - Use `/shops` to view the list of stored shops.
   - Use `/report` to generate a sales report.
   - Use `/help` to view the command guide.

## File Structure

```
wildberries_bot_tg/
├── bot.py                # Main bot script
├── config.json           # Stores API keys and shop names
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variables
├── README.md             # Project documentation
├── utils.py              # Helper functions for configuration management and logging
├── wildberries_api.py    # Wildberries API interaction (key validation, reports, metrics)
```

## Example Commands

### Add a Shop
1. `/addshop`
2. Provide the API key and shop name.

### Delete a Shop
1. `/delshop`
2. Confirm deletion.

### List Shops
1. `/shops`
2. View all saved shops.

### Generate a Report
1. `/report`
2. Select a shop (if multiple exist).
3. Choose a reporting period.
4. Receive the formatted sales report.

## Dependencies
- `aiogram`: For Telegram bot interactions
- `requests`: For API requests
- `python-decouple`: For managing environment variables

Install all dependencies using:
```bash
pip install -r requirements.txt
```

## Error Handling
- Invalid API keys are rejected with a user-friendly error message.
- Errors during API requests or bot interactions are logged and reported to the user.

## Logging
Logs are maintained to monitor bot performance and troubleshoot issues.

## Contributing
Feel free to fork this repository and submit pull requests for any improvements or fixes.


