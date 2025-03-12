
# GenBI - Generative Business Intelligence

**GenBI** is an interactive Streamlit application designed to simplify data analysis and visualization. It leverages generative AI capabilities to allow users to upload datasets, ask natural language questions, and receive insights in the form of tables, visualizations, or textual answers. Powered by pandas, LangChain, OpenAI's GPT-4o model, and Plotly, GenBI makes data exploration accessible to both technical and non-technical users.

---

## Features

- **Supported File Formats**: Upload datasets in CSV, Excel (`.xlsx`, `.xls`), or JSON formats.
- **Natural Language Queries**: Ask questions about your data in plain English (e.g., "What is the average age?" or "Show me a bar plot of sales by category").
- **Dynamic Analysis**: 
  - **Tables**: Get summarized or filtered data in tabular form.
  - **Visualizations**: Generate interactive charts using Plotly based on your queries.
  - **Answers**: Receive concise answers to statistical or descriptive questions.
- **Data Preview**: View a snapshot of your uploaded dataset, including row count and column names.
- **Error Handling**: Robust support for numeric conversion and file loading issues.

---

## Prerequisites

- Python 3.8+
- A valid OpenAI API key (for GPT-4o integration)

---

## Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/genbi.git
   cd genbi
   ```

2. **Install Dependencies**:
   Create a virtual environment and install the required packages:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the root directory and add your OpenAI API key:
   ```plaintext
   OPENAI_API_KEY=your-openai-api-key
   ```



## Usage

1. **Run the App**:
   Start the Streamlit app from the terminal:
   ```bash
   streamlit run app.py
   ```

2. **Upload a Dataset**:
   - Use the sidebar to upload a file (CSV, Excel, or JSON).
   - Preview your data, including the first few rows, total row count, and column names.

3. **Ask Questions**:
   - Enter a question in the text input field (e.g., "Show me a bar plot of sales by category" or "What is the average revenue?").
   - The app will classify your query and return a visualization, table, or text response accordingly.

4. **Explore Results**:
   - Visualizations are displayed as interactive Plotly charts.
   - Tables and answers appear below the input field.

---

## Example Queries

- **Descriptive**: "What is the average age?"
- **Tabular**: "Show me the top 5 products by sales."
- **Visualization**: "Create a bar plot of revenue by region."

---

## Project Structure

```
genbi/
├── agents/
│   ├── classifier.py         # Query classification logic
│   ├── prompt_generator.py   # Generates prompts for data manipulation
│   └── visualization.py      # Visualization creation logic
├── utils/
│   ├── data_processor.py     # Dataframe processing utilities
│   └── openai_helpers.py     # OpenAI API helpers
├── main.py                    # Main Streamlit application
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

---

## Notes

- **Security**: The app uses `allow_dangerous_code=True` in the pandas dataframe agent for flexibility. Use caution with untrusted datasets or in production environments.
- **Dependencies**: Ensure all custom modules (`agents`, `utils`) are implemented as referenced in the code.
- **Date**: This README is based on the app as of February 23, 2025.

---

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for bugs, feature requests, or improvements.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
```
