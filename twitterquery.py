import keylesstwitterpost as twitterpost
import tweepy
import sys
import psycopg2

def text_error_check(text):
    '''
    Checks the query to make sure it meets certain parameters.  If so returns
    True if not returns False

    Inputs:
    text - person twitter query converted into a list

    Outputs:
    Boolean - True or False depending on whether the query meets the parameters
    '''

    key_list = ['playerstats', 'teamstats', 'playergraph', 'teamgraph']

    for word in key_list:
        if word not in text:
            return False

    if len(text) < 4 and len(text) > 10:
        return False
    else:
        return True

def query_creation(query_list):
    if len(query_list) == 3:
        if query_list[1][0:6] == 'player':
            sql_query = 'SELECT player, ROUND((SUM(cf)/(SUM(cf)+sum(ca)))::NUMERIC, 4) * 100 as CF_Percent,'\
                        ' ROUND((SUM(xgf)/(SUM(xgf) + SUM(xga)))::NUMERIC, 4) * 100 as xGF_Percent, '\
                        'ROUND(SUM(ixg)::NUMERIC, 4)'\
                        ' FROM {} WHERE player = \'{}\' group by player;'.format(query_list[1],
                        query_list[0])
        else:
            sql_query = 'SELECT team, ROUND((SUM(cf)/(SUM(cf)+sum(ca)))::NUMERIC, 4) * 100 as CF_Percent,'\
                        ' ROUND((SUM(xgf)/(SUM(xgf) + SUM(xga)))::NUMERIC, 4) as xGF_Percent'\
                        ' FROM {} WHERE team = \'{}\' group by team;'.format(query_list[1],
                        query_list[0])
    elif len(query_list) == 4:
        if query_list[2][0:6] == 'player':
            sql_query = 'SELECT player, ROUND((SUM(cf)/(SUM(cf)+sum(ca)))::NUMERIC, 4) * 100 as CF_Percent,'\
                        ' ROUND((SUM(xgf)/(SUM(xgf) + SUM(xga)))::NUMERIC, 4) * 100 as xGF_Percent,'\
                        'ROUND(SUM(ixg)::NUMERIC, 4)'\
                        ' FROM {} WHERE player = \'{}\' or player = \'{}\' group by player;'.format(query_list[2],
                        query_list[0], query_list[1])
        else:
            sql_query = 'SELECT team, ROUND((SUM(cf)/(SUM(cf)+sum(ca)))::NUMERIC, 4) * 100 as CF_Percent,'\
                        ' ROUND((SUM(xgf)/(SUM(xgf) + SUM(xga)))::NUMERIC, 4) * 100 as xGF_Percent'\
                        ' FROM {} WHERE team = \'{}\' or team = \'{}\' group by team;'.format(query_list[2],
                        query_list[0], query_list[1])

    return sql_query


def query_parse(text_list):
    new_query = []
    if 'playerstats' in text_list and 'vs.' not in text_list:
        #append player name
        new_query.append('{}.{}'.format(text_list[1], text_list[2]).upper())
        #append database
        new_query.append(text_list[3].lower())
        #append year
        new_query.append(text_list[4])
    elif 'playerstats' in text_list and 'vs.' in text_list:
        #append first player name
        new_query.append('{}.{}'.format(text_list[1], text_list[2]).upper())
        #append second player name
        new_query.append('{}.{}'.format(text_list[4], text_list[5]).upper())
        #append database
        new_query.append(text_list[6].lower())
        #append year
        new_query.append(text_list[7])
    elif 'teamstats' in text_list and 'vs.' not in text_list:
        #append team name
        new_query.append(text_list[1].upper())
        #append database
        new_query.append(text_list[2].lower())
        #append year
        new_query.append(text_list[3])
    elif 'teamstats' in text_list and 'vs.' in text_list:
        #append first team name
        new_query.append(text_list[1].upper())
        #append second team name
        new_query.append(text_list[3].upper())
        #append database
        new_query.append(text_list[4].lower())
        #append year
        new_query.append(text_list[5])

    if 'vs.' in text_list:
        if '-adj' in text_list and '-5v5' in text_list:
            new_query[2] = '{}{}{}'.format(new_query[2], 'adj', '5v5')
        elif '-adj' in text_list and '-5v5' not in text_list:
            new_query[2] = '{}{}'.format(new_query[2], 'adj')
        elif '-adj' not in text_list and '-5v5' in text_list:
            new_query[2] = '{}{}'.format(new_query[2], '5v5')
    else:
        if '-adj' in text_list and '-5v5' in text_list:
            new_query[1] = '{}{}{}'.format(new_query[1], 'adj', '5v5')
        elif '-adj' in text_list and '-5v5' not in text_list:
            new_query[1] = '{}{}'.format(new_query[1], 'adj')
        elif '-adj' not in text_list and '-5v5' in text_list:
            new_query[1] = '{}{}'.format(new_query[1], '5v5')

    return new_query

def database_query(query):

    conn = psycopg2.connect("host=localhost dbname=nhl user=matt")
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    data = []
    for row in rows:
        data.append('{}'.format(str(row).replace('(', '').replace(',', '')\
                .replace(')', '').replace("'", '').replace('Decimal', '')))
    conn.close()

    return data

def twitter_text_parser(data_text, status_text, season):
    twitter_string = '{}\n'.format(season)
    if 'playerstats' in status_text:
        stats = ['CF%', 'xGF%', 'ixG']
        for data in data_text:
            data_list = data.split(' ')
            for stat, x in zip(stats, range(len(data_list[0:3]))):
                data_list[x+1] = '{}: {}'.format(stat, data_list[x+1][:-2])

            twitter_string += '\n'.join(data_list)
            twitter_string += '\n'
    else:
        stats = ['CF%', 'xGF%']
        for data in data_text:
            data_list = data.split(' ')
            for stat, x in zip(stats, range(len(data_list[0:2]))):
                data_list[x+1] = '{}: {}'.format(stat, data_list[x+1][:-2])

            twitter_string += '\n'.join(data_list)
            twitter_string += '\n'


    return twitter_string

class BotStreamer(tweepy.StreamListener):
# Called when a new status arrives which is passed down from the on_data method of the StreamListener
    def __init__(self, api):
        self.api = api

    def on_status(self, status):
        username = status.user.screen_name
        status_id = status.id
        status = status.text
        status = status.split(' ')
        print(status)
        if text_error_check(status):
            self.api.update_status(status = '@{} Please check your syntax and try again'.format(username), \
                    in_reply_to_status_id = status_id)
            return

        try:
            query = query_parse(status)
            query_text = query_creation(query)
            returned_data = database_query(query_text)
            tweet_text = twitter_text_parser(returned_data, status, query[-1])
            self.api.update_status(status =  '@{}\n{}'.format(username,tweet_text),\
                   in_reply_to_status_id = status_id)

        except Exception as ex:
            print(ex)
            self.api.update_status(status = '@{} Please check your syntax and try again'.format(username), \
                    in_reply_to_status_id = status_id)
            return







def main():
    '''
    Script to run a stream listener for the @barloweanalytic tiwtter bot
    so it can catch when people tweet it requests and then respond with the
    appropriate statistics

    Input:
    sys.argv[1] - the text file containing the API keys for the twitter bot

    Outputs:
    None
    '''
    twitter_keys = twitterpost.get_twitter_keys(sys.argv[1])
    auth = tweepy.OAuthHandler(twitter_keys['Consumer Key'],
            twitter_keys['Consumer Secret Key'])
    auth.set_access_token(twitter_keys['Access Key'],
            twitter_keys['Access Secret Key'])
    api = tweepy.API(auth)


    myStreamListener = BotStreamer(api)
# Construct the Stream instance
    stream = tweepy.Stream(auth = api.auth, listener = myStreamListener)
    stream.filter(track=['@barloweanalytic'])

if __name__ == '__main__':
    main()