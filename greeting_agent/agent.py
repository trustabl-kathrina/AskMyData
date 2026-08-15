import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import time
from google.adk.agents.llm_agent import Agent

# Load the file tmdb_5000_movies.csv from the project root into a pandas dataframe called df
CURRENT_CSV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tmdb_5000_movies.csv"))
try:
    df = pd.read_csv(CURRENT_CSV_PATH)
except FileNotFoundError:
    df = pd.DataFrame()

def set_dataset_path(new_path: str):
    """Updates the dataset path and reloads the global dataframe df."""
    global CURRENT_CSV_PATH, df
    CURRENT_CSV_PATH = new_path
    try:
        df = pd.read_csv(new_path)
    except FileNotFoundError:
        df = pd.DataFrame()

def get_schema() -> str:
    """Returns the column names of df and the first 3 rows as a sample."""
    columns = list(df.columns)
    sample = df.head(3).to_string()
    return f"Columns:\n{columns}\n\nSample Data (First 3 rows):\n{sample}"

def run_query(pandas_expression: str) -> str:
    """Evaluates a pandas expression against the dataframe df using eval() and returns the result.
    
    Args:
        pandas_expression: A valid pandas expression as a string (e.g. "df['title'].head(5)" or "df[df['budget'] > 100000000]['title']").
    """
    try:
        result = eval(pandas_expression, {"df": df, "pd": pd})
        return str(result)
    except Exception as e:
        return f"Error executing query: {str(e)}"

def plot_chart(chart_type: str, column: str, group_by_column: str = None, title: str = "Chart") -> str:
    """Creates a chart from df using matplotlib and saves it as a uniquely named PNG file.
    
    Args:
        chart_type: The type of chart ("bar", "histogram", "pie", or "line").
        column: The column to plot (or aggregate).
        group_by_column: Optional column to group by.
        title: The title of the chart.
    """
    plt.figure(figsize=(10, 6))
    try:
        if chart_type == "bar":
            if group_by_column:
                # Check if column is numeric for mean, otherwise do count
                if pd.api.types.is_numeric_dtype(df[column]):
                    data = df.groupby(group_by_column)[column].mean()
                    ylabel = f"Mean of {column}"
                else:
                    data = df.groupby(group_by_column)[column].count()
                    ylabel = "Count"
                # Keep top 15 groups if there are too many to avoid overlapping labels
                if len(data) > 15:
                    data = data.sort_values(ascending=False).head(15)
                    title += " (Top 15)"
                data.plot(kind="bar")
                plt.ylabel(ylabel)
                plt.xlabel(group_by_column)
            else:
                # Bar chart of value counts
                data = df[column].value_counts().head(15)
                data.plot(kind="bar")
                plt.ylabel("Count")
                plt.xlabel(column)
        elif chart_type == "histogram":
            # Plot histogram of the column
            df[column].plot(kind="hist", bins=20, edgecolor='black')
            plt.xlabel(column)
            plt.ylabel("Frequency")
        elif chart_type == "pie":
            # Use top categories by count
            if group_by_column:
                data = df.groupby(group_by_column)[column].count()
            else:
                data = df[column].value_counts()
            # Limit to top 8 categories to keep pie chart readable
            if len(data) > 8:
                top_data = data.sort_values(ascending=False).head(8)
                other_sum = data.sort_values(ascending=False).iloc[8:].sum()
                top_data["Other"] = other_sum
                data = top_data
            data.plot(kind="pie", autopct='%1.1f%%', startangle=90)
            plt.ylabel("") # Remove the y-label for pie charts
        elif chart_type == "line":
            if group_by_column:
                # If grouping, sort by the group_by_column index
                if pd.api.types.is_numeric_dtype(df[column]):
                    data = df.groupby(group_by_column)[column].mean()
                    ylabel = f"Mean of {column}"
                else:
                    data = df.groupby(group_by_column)[column].count()
                    ylabel = "Count"
                data = data.sort_index()
                data.plot(kind="line", marker='o')
                plt.ylabel(ylabel)
                plt.xlabel(group_by_column)
            else:
                # Just plot the column values, sorted by index
                data = df[column]
                data.plot(kind="line")
                plt.ylabel(column)
        else:
            plt.close()
            return f"Error: Unsupported chart_type '{chart_type}'. Supported types are 'bar', 'histogram', 'pie', and 'line'."
        
        plt.title(title)
        if chart_type != "pie":
            plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save the chart as a unique filename in the project root folder (one level up from this file)
        filename = f"chart_{int(time.time() * 1000)}.png"
        save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", filename))
        plt.savefig(save_path)
        plt.close()
        
        # Generate a descriptive sentence for what the chart shows
        desc = f"This is a {chart_type} chart showing {column}"
        if group_by_column:
            desc += f" grouped by {group_by_column}"
        desc += "."
        
        return f"CHART_GENERATED:{filename} - {desc}"
    except Exception as e:
        plt.close()
        return f"Error generating chart: {str(e)}"

root_agent = Agent(
    model='gemini-2.5-flash',
    name='ask_my_data_agent',
    description='A data analyst assistant for the movies dataset.',
    instruction=(
        "You are a data analyst assistant for a movie dataset. Always call get_schema first "
        "if you don't already know the columns, then call run_query with a pandas expression "
        "or plot_chart to answer the user's question. If the user asks to see, visualize, "
        "plot, or show a chart/graph, use the plot_chart tool. Supported chart types are: "
        "bar, histogram, pie, and line. If a chart was generated, "
        "you must include the exact text 'CHART_GENERATED:<filename> - <one sentence description>' "
        "in your response. When answering a question about a specific value (like highest budget, "
        "average rating, most common genre), always state the actual data value in your answer, "
        "not just the name. Always answer in a clear, natural sentence, never show raw code to the user."
    ),
    tools=[get_schema, run_query, plot_chart],
)
