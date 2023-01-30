from jsonclient import JsonClient

client = JsonClient('https://api.tibber.com/v1-beta/gql')
client.inject_token('v5_PcjPxjHY-3E5HLQVFGur48SZu0AkUUzOfCthOS5M')

result = client.execute('''{
  viewer {
    homes {
      currentSubscription{
        priceInfo{
          current{
            total
            startsAt
          }
          today {
            total
            startsAt
          }
          tomorrow {
            total
            startsAt
          }
        }
      }
    }
  }
}

''')
print(result)