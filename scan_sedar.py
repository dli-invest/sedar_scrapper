import pandas as pd 
import os
import json
import requests
from io import StringIO
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

# send csv to discord webhook

def post_buffer_to_discord(url: str, file: str, filename: str = 'file'):
  url = url
  result = requests.post(
      url, files={filename: file}
  )
  try:
      result.raise_for_status()
  except requests.exceptions.HTTPError as err:
      print(err)
  else:
      print("Image Delivered {}.".format(result.status_code))

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
    merged_df: pd.DataFrame = new_df.merge(legacy_df,indicator = True, on=["Company Name","Date of filing","Time of filing","Document Type","File Format","File Size"], how='left').loc[lambda x : x['_merge']=='left_only']
    full_df = pd.concat([new_df, legacy_df]).drop_duplicates(keep="first")
    full_df.to_csv(csv_name, index=False)
    
    if len(merged_df) > 0:
        url = os.getenv("DISCORD_WEBHOOK")
        # send csv to discord
        textstream = StringIO()
        merged_df.to_csv(textstream, encoding='utf-8', index=False)
        # get current date in YYYY-MM-DD format
        date = time.strftime("%Y-%m-%d")
        filename = f"sedar_docs_{date}.csv"
        post_buffer_to_discord(url, textstream.getvalue(), filename={filename})
        

def main(url="https://www.sedar.com/new_docs/all_new_pc_filings_en.htm"):
    # parse html from tables.html using pandas
    pd_df = pd.read_html('tables.html')
    parse_table(pd_df[0])
    pass

if __name__ == "__main__":
    main()
