import grequests
import time
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6ImRmYXNkZjMyIiwicm9sZSI6MSwiaWF0IjoxNjUzMzU4MjUyfQ.JG8L-1-jzIZA03OuOTKsi7EIsU_tKVe7y9WCD0xzAJw"
SERVER_URL="http://aiot-jsc.ddns.net:8000/calib"
while True:
    res= grequests.get(SERVER_URL,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/json','Content-Type': 'application/json'})
    # print(res)
    a= grequests.map([res],gtimeout=1)
    
    # if res.status_code>=200 and res.status_code <400:
    #     print('get server success!')
    #     data = res.json()
    #     print(data['code'])
    if a[0]!=None:
        print(a[0].status_code)
        data= a[0].json()
        print(data)
    else:
        print('no internet')
    time.sleep(1)