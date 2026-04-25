# Contributing Guidelines

## Code of Conduct

This project adheres to a Contributor Code of Conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs
- Use the GitHub Issues tracker
- Check if the issue already exists
- Include as much relevant information as possible
- Include code samples and expected vs. actual behavior

### Submitting Enhancements
- Clearly describe the enhancement and its benefits
- Include code examples where applicable
- Follow the code style guidelines

### Pull Requests
1. Fork the repository and create a feature branch
2. Follow the code style guidelines
3. Add tests for new functionality
4. Ensure all tests pass: `pytest tests/ -v`
5. Commit with clear, descriptive messages
6. Push to your fork and submit a pull request

## Code Style Guidelines

- Use Black for code formatting: `black app worker`
- Use isort for import sorting: `isort app worker`
- Follow PEP 8
- Use type hints where possible
- Maximum line length: 100 characters

## Testing

- Write tests for new features
- Maintain >80% code coverage
- Run tests before submitting PR: `pytest tests/ --cov=app --cov=worker`

## Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions and classes
- Update ARCHITECTURE.md for structural changes

## Development Setup

1. Clone repository: `git clone <repo>`
2. Install dev dependencies: `pip install -r requirements.txt`
3. Install pre-commit hooks: `pre-commit install`
4. Create feature branch: `git checkout -b feature/your-feature`
5. Make changes and test
6. Submit pull request

## Questions?

Open a GitHub Discussion or reach out to maintainers.

Thank you for contributing! 🙏
