Travel Assistant — AI-Powered Hotel Search

A web application that helps users discover hotel offers using natural language.

Built with Python, Flask, OpenAI API, and Nuitee API.

Features

- Natural language search: Users can describe their hotel preferences in everyday language.
- AI-powered request processing: OpenAI helps interpret search requests.
- Hotel API integration: Retrieves hotel offers through Nuitee.
- Price filtering: Supports maximum accommodation budgets.
- Sorting: Displays hotel offers by price.
- Hotel details: Shows hotel names, locations, prices, and available images.
- Error handling: Handles invalid requests and external API failures.
- Automated testing: Includes tests for important application functionality.
- Cloud deployment: Hosted on Render.

Technology Stack

- Python
- Flask
- OpenAI API
- Nuitee API
- REST APIs and JSON
- HTML and CSS
- Gunicorn
- GitHub
- Render

How It Works

1. The user enters a hotel search request.
2. OpenAI processes the natural language input.
3. The application prepares structured search parameters.
4. Nuitee API provides hotel offer data.
5. The application filters and sorts the results.
6. Available hotels are displayed in the web interface.

Project Structure

- "app.py" — Flask application and HTTP routes
- "ai_service.py" — OpenAI integration
- "hotel_service.py" — Hotel search and API integration
- "config.py" — Configuration and API credentials
- "templates/" — HTML templates
- "static/" — CSS and static assets
- "tests/" — Automated tests
- "requirements.txt" — Python dependencies
- "Procfile" — Application startup configuration

Deployment

The application is deployed using Render and Gunicorn.

API credentials are configured through environment variables rather than being stored in the public source code.

Important Notice

The current Nuitee integration uses demonstration data. Displayed hotel offers and prices are not intended for real bookings.

Project Status

Deployed prototype — successfully tested with natural language hotel searches and hotel offer results.

Author

EduardK15

GitHub: https://github.com/EduardK15
