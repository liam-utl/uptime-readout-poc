import requests
import json
import datetime
from decimal import Decimal
from pathlib import Path
import pandas as pd
import os

# Functions to convert datetime format to nano and visa versa
def dateTimeToNano(dateTime):
    unix_timestamp = datetime.datetime.timestamp(dateTime) * 1000000000
    return int(Decimal(unix_timestamp))


def nanoToDateTime(nano):
    dt = datetime.datetime.fromtimestamp(nano // 1000000000)
    s = dt.strftime("%Y-%m-%d %H:%M:%S")
    return s

def process_data(df, convert_names=True, convert_dates=True):
    # TODO - Check anonmysation of player name when using /incident command
    today = datetime.date.today()
    today = today.strftime("%Y%m%d")

    df = df[['datetime', 'player', 'scenario', 'level', 'session_id', 'channel', 'message']]
    # Only keep the message part of 'message'
    df['message'] = df['message'].astype(str)
    df['message'] = df['message'].str.split(':', n=1).str[-1]
    df['message'] = df['message'].str.rsplit('[', n=1).str[0]
    # Trim any leading or trailing spaces
    df['message'] = df['message'].str.strip()

    if convert_dates:
        # Convert datetime column to YYYY-MM-DD HH:MM:SS format
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['datetime'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Symbols and character mentions must be mapped to their correct strings
    # For player mentions, these still remain coded as different for every player
    symbol_map = {
        "&#39;": "'",
        "&#x60;": "`",
        "&#x2F;": "/",
        "&#x3D;": "=",
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
        "&quot;": '"',
    }
    player_map = {
        "<@U047N6MGH19>": "@Shay",
        "<@U047N6LHU0K>": "@Daniel",
        "<@U047N90R8KU>": "@Bez",
        "<@U047KAE5JLV>": "@Tinus",
        "<@U047N6LUYJX>": "@Tanya",
        "<@U047N91SRH8>": "@Bob",
        "<@U0480TP9ZA5>": "@Hamed",
        "<@U047QNHDG6Q>": "@Jane",
    }

    messages = df["message"].tolist()

    lex_intents = []
    lex_scores = []
    formatted_messages = []
    length_of_messages = []
    questions = []
    processed_count = 0

    for message in messages:
        # Replace symbols and character mentions with their correct strings
        for code, character in symbol_map.items():
            message = message.replace(code, character)

        if convert_names:
            for code, character in player_map.items():
                message = message.replace(code, character)

            # Any unmapped character mentions must be player mentions, and replaced with '@Player'
            if "<@U0" in message:
                index1 = message.find("<@U0")
                # Player code is 14 characters long
                index2 = index1 + 14
                player_code = message[index1:index2]
                message = message.replace(player_code, "@Player")

        formatted_messages.append(message)

        message_length = len(message)
        length_of_messages.append(message_length)

        # Question only identified through presence of '?' - needs to be changed in future
        question = False
        if "?" in message:
            question = True
        questions.append(question)
        
        processed_count += 1
        if processed_count % 1000 == 0:
            print(f"Processed {processed_count}/{len(messages)} messages")


    df["message"] = formatted_messages
    df["length_of_message"] = length_of_messages
    df["question"] = questions
    df.sort_values(by=["session_id", "datetime"])

    return df

def get_raw_loki_data_by_session(session_id, hours=1):
    today = datetime.date.today()
    today = today.strftime("%Y%m%d")

    # X-Scope-OrgID configuration - can switch between 'fake' and 'uptimelabs'
    x_scope_org_id = "uptimelabs"  # default value, can be changed to "uptimelabs"

    # obtain a new OAuth 2.0 token from the authentication server
    client_id = "loki"
    client_secret = os.getenv("LOKI_TOKEN")
    loki_domain = os.getenv("LOKI_URL")

    server_prod = f"id.{loki_domain}.uptimelabs.io"

    auth_server_url = (
        "https://" + server_prod + "/realms/tenants/protocol/openid-connect/token"
    )

    token_req_payload = {"grant_type": "client_credentials"}

    try:
        token_response = requests.post(
            auth_server_url,
            data=token_req_payload,
            verify=False,
            allow_redirects=False,
            auth=(client_id, client_secret),
        )
        
        if token_response.status_code != 200:
            raise Exception(f"Failed to get token: {token_response.status_code}")
        
        tokens = json.loads(token_response.text)
        
        if "access_token" not in tokens:
            raise KeyError("access_token not found in token response")
        
        token = tokens["access_token"]
        
    except Exception as e:
        print("Loki API authentication failed. Please check your credentials.")
        raise

    # Request loki api data and save in list
    results_present = True
    thirty_day_period = 0
    data = []
    final_df = pd.DataFrame()

    while results_present:
        # So save data, only request the last hour of data
        end_date = dateTimeToNano(
            datetime.datetime.now() - datetime.timedelta(thirty_day_period)
        )
        start_date = dateTimeToNano(
            datetime.datetime.now() - datetime.timedelta(hours=hours)
        )

        loki_prod_url = f'https://loki.{loki_domain}.uptimelabs.io/loki/api/v1/query_range?direction=BACKWARD&limit=50000&query={{session_id%3D"{session_id}",app%3D"slack"}}&start={start_date}&end={end_date}&step=300'

        # loki_prod_url = f'https://loki.prod.uptimelabs.io/loki/api/v1/query_range?direction=BACKWARD&limit=50000&query={{app%3D"slack"}}&start={start_date}&end={end_date}&step=300'
        api_call_headers = {
            "Authorization": "Bearer " + token,
            "X-Scope-OrgID": x_scope_org_id
        }
        
        try:
            api_call_response = requests.get(
                loki_prod_url, headers=api_call_headers, verify=False
            )
            
            
            if api_call_response.status_code != 200:
                print(f"API call failed with status {api_call_response.status_code}")
                break
                
            data_dict = json.loads(api_call_response.text)
            
            if "data" not in data_dict:
                print(f"'data' key not found in response. Keys: {list(data_dict.keys())}")
                break
                
            results = data_dict["data"]["result"]
            
            if not results:
                print("No more results found, ending data extraction")
                results_present = False
                continue
                
        except Exception as e:
            print(f"Error making API call: {str(e)}")
            break

        records_processed = 0
        for result in results:
            for i in range(len(result["values"])):
                record = {'datetime':None, 'player':None, 'player_name':None, 'scenario':None, 'level':None, 'channel':None, 
                        'session_id':None, 'infra':None, 'app':None, 'message':None, 'neutral':None, 'negative':None, 'positive':None, 'mixed':None, 
                        'sentiment':None}
                value = result['values'][i]

                record['datetime'] = int(value[0])
                record['message'] = value[1]

                for key in record:
                    if key in result['stream']:
                        record[key] = result['stream'][key]
                
                data.append(record)
                records_processed += 1

        # Store loki data in dataframe and save as csv
        df = pd.DataFrame(data)
        df = df.sort_values(by=["session_id", "datetime"])
        df = df.reset_index(drop=True)
        return df

def get_session_chat(session_id: str):
    raw_df = get_raw_loki_data_by_session(session_id, hours = 720)
    # raw_df = loki_logs.get_raw_loki_log_by_session_id(session_id=session_id, hours=4, save_locally=False)
    
    if raw_df.empty:
        return f"No data found for session_id: {session_id}"
    
    print(f"RAW DF: {raw_df.shape}")

    processed_df = process_data(raw_df)
    # processed_df.to_csv('processed_loki_data.csv', index=True)
    print(f"PROCESSED DF: {processed_df.shape}")
    print(processed_df['session_id'].unique())

    filter_df = processed_df[processed_df['session_id'] == session_id]
    print(f"FILTERED DF: {filter_df.shape}")
    print(filter_df.head())

    # filter out any rows there player is UptimeLabs
    filter_df = filter_df[filter_df['player'] != 'UptimeLabs']

    level = filter_df['level'].unique()
    # where player contains and email address, replace it with "PLAYER"
    filter_df['player'] = filter_df['player'].str.replace(r'\S+@\S+\.\S+', 'PLAYER', regex=True)

    # remove scenario, session_id, and level columns
    filter_df = filter_df.drop(columns=['scenario', 'session_id', 'level', 'question', 'length_of_message'])

    return filter_df

