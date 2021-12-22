import json
from pathlib import Path

import pandas as pd
from matplotlib import pyplot as plt


def flatten_json(y):
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '.')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '.')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(y)
    return out


if __name__ == '__main__':
    # get all lines from all log files
    log_lines = []
    for path in sorted(Path('logs').glob('*.log')):

        # exclude dev-redirect logs
        if 'redirect' in path.name:
            continue

        print(path)
        with path.open('rb') as f:
            for i, line in enumerate(f):
                try:
                    line = line.decode('utf8')
                except UnicodeDecodeError as e:  # some regret not setting encoding right from the start
                    print(e)
                    line = line.decode('latin1')
                    print(i, line)
                log_lines.append(line)

    # flatten all message jsons into dataframe rows
    rows = []
    for line in log_lines:
        if '\tMESSAGE_JSON=' in line:
            rows.append(flatten_json(json.loads(line.split('\tMESSAGE_JSON=', 1)[1])))
    len(rows)

    # load dataframe
    df = pd.DataFrame(rows)
    df['datetime'] = pd.to_datetime(df['message.date'], unit='s') + pd.Timedelta(hours=8)
    df['date'] = df['datetime'].dt.date
    df['time'] = df['datetime'].dt.time

    # df of everyone who isn't myself
    df_others = df[(df['message.message_id'].notna()) &
                   (df['message.from.username'] != 'averykhoo')
                   ].dropna(axis='columns', how='all')

    # plot usage by day / hour
    df_others['date'].value_counts().sort_index().plot(figsize=(20, 10))
    plt.show()
    df_others['time'].apply(lambda t: str(t)[:2]).value_counts().sort_index().plot(figsize=(20, 10))
    plt.show()

    # when was the first seen time of a user
    first_seen = dict(df_others.groupby('message.from.id')['datetime'].min())
    df_others['user_first_seen_datetime'] = [first_seen[user_id] for user_id in df_others['message.from.id']]
    df_others['is_first_seen'] = df_others['datetime'] <= df_others['user_first_seen_datetime']

    # plot when new users first see the bot
    df_others.groupby('date')['is_first_seen'].sum().sort_index().plot(figsize=(20, 10))
    plt.show()

    # save dataframe
    df_others.to_excel('hawker-bot-logs.xlsx')
