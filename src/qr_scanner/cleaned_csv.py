import pandas as pd
import os

def remove_duplicate_qr_entries(input_filename, output_filename, key_column='QR_Text'):
    """
    Reads a CSV file, removes duplicate rows based on the specified key column,
    and saves the unique entries to a new CSV file.

    Args:
        input_filename (str): The path to the original CSV file (e.g., 'qr_scanned_data.csv').
        output_filename (str): The path for the de-duplicated CSV file.
        key_column (str): The column header to check for duplicate values.
                          (Default is 'QR_Text').
    """
    if not os.path.exists(input_filename):
        print(f"Error: Input file '{input_filename}' not found.")
        return

    try:
        # 1. Read the CSV into a pandas DataFrame
        df = pd.read_csv(input_filename)
        print(f"Original file loaded. Total rows: {len(df)}")

        # 2. Check for the required column
        if key_column not in df.columns:
            print(f"Error: Column '{key_column}' not found in the CSV header. Available columns: {list(df.columns)}")
            return

        # 3. Remove duplicates
        # 'subset' specifies the column(s) to check for duplicates.
        # 'keep="first"' ensures the first occurrence of a duplicate row is kept.
        df_cleaned = df.drop_duplicates(subset=[key_column], keep='first')

        # 4. Save the de-duplicated data to the new file
        # index=False prevents pandas from writing the row index numbers to the CSV.
        df_cleaned.to_csv(output_filename, index=False)

      

    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")

# --- Execution ---
if __name__ == "__main__":
    # Define your file paths
    # Assuming your scanned data is saved here:
    input_file = "logged_data.csv"
    # The clean results will be saved here:
    output_file = "cleaned_data.csv"

    # Run the function
    remove_duplicate_qr_entries(input_file, output_file)