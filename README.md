# cpeTranslater2
用於將軟體名稱轉換成CPE(Common Platform Enumeration)格式的值。

為了節省人工比對的時間，做了一個可以自動比對的小工具。
    
將軟體名稱自動轉成CPE格式的值，方便後續匯整後，匯入到技服中心的VANS系統。

線上版：利用NIST的API做查詢，並找出最接近的值。
sqlite版：下載NIST的XML檔，然後比對找出最接近的值（受到info2cpe啟發）。

比對結果會有部份誤差，還在調整中。

中文軟體一律跳過不比對！
