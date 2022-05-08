import pandas as pd 
import os
import json
import requests
import time

def post_webhook_content(url, data: dict):
    try:
        result = requests.post(
            url, data=json.dumps(data), headers={"Content-Type": "application/json"}
        )
        result.raise_for_status()
    except requests.exceptions.HTTPError as err:
        status_code = err.response.status_code
        if status_code == 429:
            print("Rate limited by discord")
            # wait for a minute
            time.sleep(60)
            post_webhook_content(url, data)
    else:
        print("Payload delivered successfully, code {}.".format(result.status_code))

def is_unique(s):
    a = s.to_numpy() # s.values (pandas<0.24)
    return (a[0] == a).all()

def parse_table(df: pd.DataFrame):
    csv_name = "sedar_docs.csv"
    old_columns = ["r1", "r2", "r3", "r4", "r5", "r6"]
    columns = ["Company Name", "Date of filing", "Time of filing", "Document Type", "File Format", "File Size"]
    df.columns = old_columns
    new_df = pd.DataFrame(columns=columns)
    company_name = ""
    for index, row in df.iterrows():
        unique_rows = row.nunique()
        # for sedar docs 0 unique values means padding row
        if unique_rows == 0:
            company_name = ""
            pass
        # pandas seems to be repeating the company name for each row
        elif unique_rows == 1:
            # company name here
            company_name = row["r2"]
            pass

        elif unique_rows == 5:
            # useful data is here
            # grab data from r2 to r6
            new_df_row = pd.DataFrame({'Company Name': [company_name],
                    'Date of filing' : [row["r2"]],
                    'Time of filing' : row["r3"],
                    "Document Type" : row["r4"],
                    "File Format" : row["r5"], 
                    "File Size" : row["r6"]})
            new_df = pd.concat([new_df, new_df_row])
    legacy_df = pd.read_csv(csv_name)
    merged_df = new_df.merge(legacy_df,indicator = True, how='left').loc[lambda x : x['_merge']=='right_only']
    full_df = pd.concat([new_df, legacy_df]).drop_duplicates(keep="first")
    full_df.to_csv(csv_name, index=False)
    # too many entries to send, just keep saving all the sedar docs for now
    print(merged_df)
    if len(merged_df) > 0:
        url = os.getenv("DISCORD_WEBHOOK")
        df_string = merged_df.to_string(header=True, index=False)
        # send row results to discord via csv
        # split into chunks of 2000
        chunks = [df_string[i:i+1990] for i in range(0, len(df_string), 1990)]
        for chunk in chunks:
            post_webhook_content(url, {"content": chunk})
            time.sleep(2)
        else:
            print("NO CHUNKS")
            print(df_string)
            post_webhook_content(url, {"content": df_string})
        pass

def main(url="https://www.sedar.com/new_docs/all_new_pc_filings_en.htm"):
    # parse html from tables.html using pandas
    pd_df = pd.read_html('tables.html')
    parse_table(pd_df[0])
    pass

if __name__ == "__main__":
    main()
