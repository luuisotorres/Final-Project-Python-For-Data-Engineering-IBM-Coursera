import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
import sqlite3

def log_progress(message, log_file="code_log.txt"):
    """
    This function logs a message to the log_file with a timestamp.

    Params:
    messsage (str) -> The message that will be logged
    log_file (str) -> The name of the file where logs will be registered.
    """

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n\n"

    with open(log_file, "a") as logf:
        logf.write(log_entry)

def extract():
    """
    This function extracts the table under 'By market capitalization' and returns it 
    as a Pandas DataFrame
    """

    url = "https://web.archive.org/web/20230908091635/https://en.wikipedia.org/wiki/List_of_largest_banks"

    log_progress("Starting Extract phase...")
    
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table", {
        "class":"wikitable"
        }
    )

    # Selecting all rows within the table (<tr> tag)
    rows = table.find_all("tr")

    # Extracting headers from the first row
    headers = [header.text.strip() for header in rows[0].find_all("th")]

    # Extracting data from the next rows
    data = []
    for row in rows[1:]:
        # Selecting all columns within each row
        cells = row.find_all("td")
        
        cell_values = [cell.text.strip() for cell in cells]
        if cell_values:
            data.append(cell_values)

    # Creating DataFrame with the extracted data
    df = pd.DataFrame(data, columns=headers)

    # Removing 'Rank' column
    df = df.drop("Rank", axis=1)

    # Renaming columns
    df = df.rename(columns={
        "Bank name":"Name",
        "Market cap(US$ billion)": "MC_USD_Billion"
    })

    # Removing Index
    df.reset_index(drop=True, inplace=True)

    log_progress("Extract phase completed!")

    # Returning the DF
    return df

def transform(df):
    """
    This function takes the exchange rates from the CSV file to create new columns for 
    Market Cap in British pound sterling (GBP), Euro, and Indian Rupee (INR).
    """

    log_progress("Starting Transform phase...")

    exchange_rate_csv_path = "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/IBMSkillsNetwork-PY0221EN-Coursera/labs/v2/exchange_rate.csv"

    exchange_rate_df=pd.read_csv(exchange_rate_csv_path)

    # Converting data into a dictionary
    rate_dict = dict(zip(exchange_rate_df["Currency"],
                         exchange_rate_df["Rate"]))
    
    # Converting MC_USD_Billion to numeric
    df["MC_USD_Billion"] = pd.to_numeric(df["MC_USD_Billion"],
                                         errors="coerce")
    
    # Creating new columns for converted GBP, EUR, and INR values
    df["MC_GBP_Billion"] = df["MC_USD_Billion"] * rate_dict["GBP"]
    df["MC_EUR_Billion"] = df["MC_USD_Billion"] * rate_dict["EUR"]
    df["MC_INR_Billion"] = df["MC_USD_Billion"] * rate_dict["INR"]

    # Rounding to 2 decimal 
    df["MC_GBP_Billion"] = df["MC_GBP_Billion"].round(2)
    df["MC_EUR_Billion"] = df["MC_EUR_Billion"].round(2)
    df["MC_INR_Billion"] = df["MC_INR_Billion"].round(2)

    log_progress("Transform phase completed!")

    return df
    
def load(df):
    """
    This function saves the input DataFrame to a CSV file at the specified path.
    """
    log_progress("Starting Load phase...")

    output_csv_path = "./Largest_banks_data.csv"

    df.to_csv(output_csv_path, index=False)

    log_progress("Load phase completed!")

def load_to_db(df):
    """
    This function saves the DataFrame to a SQLite database table.
    """

    log_progress("Saving table to SQLite database...")

    db_path = "Banks.db"
    table_name = "Largest_banks"

    # Creating a connection to the SQLite database
    conn = sqlite3.connect(db_path)

    df.to_sql(table_name, conn, if_exists="replace",index=False)

    # Closing database connection
    conn.close()

    log_progress(f"DataFrame successfully loaded to {db_path} in table '{table_name}'!")
    
def run_queries():
    """
    This function runs some queries on the 'Largest_banks' table on the SQLite database.
    """

    log_progress("Running queries...")

    db_path = "Banks.db"

    conn = sqlite3.connect(db_path)

    queries = {
        "Count rows": "SELECT COUNT(*) AS row_count FROM Largest_banks;",
        "Top 5 MC_USD_Billion": """
            SELECT Name, MC_USD_Billion
            FROM Largest_banks
            ORDER BY MC_USD_Billion DESC
            LIMIT 5;
        """
    }

    results = {}
    for desc, sql_query in queries.items():
        cursor = conn.execute(sql_query)
        data = cursor.fetchall()

        # Saving results into a Pandas DataFrame
        col_names = [description[0] for description in cursor.description]
        query_result_df = pd.DataFrame(data, columns=col_names)

        results[desc] = query_result_df
    
    conn.close()

    log_progress("Queries completed!")
    return results

if __name__ == '__main__':
    log_progress("ETL Script started!")

    df_extracted = extract()

    df_transformed = transform(df_extracted)

    load(df_transformed)

    load_to_db(df_transformed)

    query_results = run_queries()
    for query_desc, qdf in query_results.items():
        log_progress(f"Query: {query_desc}\n{qdf}")

    log_progress("Script finished!")