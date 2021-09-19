import streamlit as st
import numpy as np
import pandas as pd
import datetime
from pycoingecko import CoinGeckoAPI
cg = CoinGeckoAPI()
from datetime import date, timedelta
import dateutil.parser
pd.options.plotting.backend = "plotly"


#calls list of all coins and caches them
@st.cache(show_spinner=False)
def API_coins():
    ph_all_CCs = cg.get_coins_list()
    return(ph_all_CCs)
all_CCs = API_coins()



#heading
st.title("Portfolio Tracker")

raw_data = st.file_uploader('Upload your transactions from EasyCrypto', type=['csv'])
if raw_data is not None:
    raw_df = pd.read_csv(raw_data)
    raw_df = raw_df.drop(columns=['Order','Type','Address','Memo'])
    cleaned_df = raw_df
    graph_df = raw_df.copy()
    if st.sidebar.checkbox('Show transaction history'):
        # pulls exchange rate validating CC vs list
        empty_list = []
        #move outside and create function. Ref here
        for i in cleaned_df['Coin']:
            CC = next(item for item in all_CCs if item["symbol"] == i.lower())
            id = CC['id']

            # cached function to pull "X" coin from API
            @st.cache(show_spinner=False)
            def coin_rate():
                ph_CCex_dict = cg.get_price(ids=id, vs_currencies='nzd')
                return (ph_CCex_dict)
            CCex_dict = coin_rate()
            CCex = list(list(CCex_dict.values())[0].values())[0]
            empty_list.append(CCex)
        cleaned_df['Purchase Rate'] = cleaned_df['NZD']/cleaned_df['Amount']
        cleaned_df = cleaned_df.join(pd.DataFrame({'Current Rate': empty_list}))
        cleaned_df['Current Value'] = cleaned_df['Current Rate'] * cleaned_df['Amount']
        cleaned_df['Profit'] = cleaned_df['Current Value'] - cleaned_df['NZD']
        cleaned_df['%Profit'] = cleaned_df['Profit'] / cleaned_df['NZD'] * 100

        invested = 'Invested (NZD): $' + str(cleaned_df['NZD'].sum())
        profit = 'Profit (NZD): $' + str(round(cleaned_df['Profit'].sum(),2))
        balance = 'Balance (NZD): $' + str(round(cleaned_df['Current Value'].sum(),2))
        per_prof = 'Profit: ' + str(round(cleaned_df['Profit'].sum()/cleaned_df['NZD'].sum()*100,2)) + '%'
        st.write(cleaned_df)
        st.write(invested)
        st.write(profit)
        st.write(balance)
        st.write(per_prof)

    if st.sidebar.checkbox('Show graphic history'):
        sdate = st.sidebar.date_input('start date', datetime.date(2021, 6, 16))
        edate = st.sidebar.date_input('end date', datetime.date.today())

        ownedCCtype = graph_df['Coin'].drop_duplicates()

        adjsdate = sdate
        fsdate = adjsdate.strftime('%d/%m/%Y')
        st_ts = dateutil.parser.parse(fsdate, dayfirst=True).timestamp()

        # converts end date to UNIX
        adjedate = edate + timedelta(days=1)
        fedate = adjedate.strftime('%d/%m/%Y')
        ed_ts = dateutil.parser.parse(fedate, dayfirst=True).timestamp()


        # parse API data for owned currancies into dataframe
        history_df = pd.DataFrame()
        for i in ownedCCtype:
            CC = next(item for item in all_CCs if item["symbol"] == i.lower() and item["id"][:11] != 'binance-peg')
            id = CC['id']

            #look at creating function
            @st.cache(show_spinner=False)
            def coin_hist():
                ph_rhist_dict = cg.get_coin_market_chart_range_by_id(id=id, vs_currency='nzd', from_timestamp=st_ts,
                                                              to_timestamp=ed_ts)
                return (ph_rhist_dict)
            rhist_dict = coin_hist()
            rhist = rhist_dict['prices']

            np_data = np.array(rhist)
            test_df = pd.DataFrame(data=np_data, columns=['Date', 'Past Rate ' + i])
            history_df['Past Rate ' + i] = test_df['Past Rate ' + i]
            history_df['Date'] = test_df['Date']
        history_df['Date'] = pd.to_datetime(history_df['Date'], unit='ms')

        # UNIX date to string date for matching
        history_df['Date'] = history_df['Date'].dt.tz_localize('UTC').dt.tz_convert('Pacific/Auckland')
        history_df['Date'] = history_df['Date'].dt.date
        history_df['Date'] = pd.to_datetime(history_df['Date'], format='%Y-%m-%d').dt.strftime('%d-%m-%Y')

        # splitting my data into info per crypto type and matching the dates to the historical data
        ls_ownedCCtype = ownedCCtype.tolist()
        crypto_trimmed_df = graph_df.drop(columns=['Amount'])
        crypto_trimmed_df['Date'] = pd.to_datetime(crypto_trimmed_df['Date'], format='%Y-%m-%d %H:%M:%S').dt.strftime('%d-%m-%Y')

        last_df = history_df
        for i in ls_ownedCCtype:
            placeholder = crypto_trimmed_df.drop(crypto_trimmed_df[crypto_trimmed_df.Coin != i].index)
            placeholder.columns = ['Date', i + '_Cypto', i + '_NZD']
            last_df = last_df.merge(placeholder, how='left', on='Date').fillna(0)

        # calcultations for running profit
        for i in ls_ownedCCtype:
            last_df[i + ' owned'] = last_df[i + '_NZD'] / last_df['Past Rate ' + i]
            last_df[i + ' owned'] = last_df[i + ' owned'].cumsum()
            last_df[i + ' value'] = last_df[i + ' owned'] * last_df['Past Rate ' + i]
            last_df[i + '_NZD'] = last_df[i + '_NZD'].cumsum()
            last_df[i + ' Profit'] = last_df[i + ' value'] - last_df[i + '_NZD']
            last_df[i + ' Profit %'] = (last_df[i + ' Profit'] / last_df[i + '_NZD']) * 100

        # segrigating porfit data and date into wide format df
        last_df_prof = last_df[["Date"]].copy()
        last_df_prof['Date'] = pd.to_datetime(last_df_prof['Date'], dayfirst=True)
        for i in ls_ownedCCtype:
            last_df_prof[i + ' Profit'] = last_df[i + ' Profit']
        last_df_prof = last_df_prof.set_index('Date')

        # calculating total profits
        last_df_prof["Total Profit"] = last_df_prof.sum(axis=1)
        #st.write(last_df_prof)
        # segrigating porfit percentage and date into wide format df
        last_df_prof_perc = last_df[["Date"]].copy()
        last_df_prof_perc['Date'] = pd.to_datetime(last_df_prof_perc['Date'], dayfirst=True)
        for i in ls_ownedCCtype:
            last_df_prof_perc[i + ' Profit %'] = last_df[i + ' Profit %']
        last_df_prof_perc = last_df_prof_perc.set_index('Date')

        last_df_prof_perc["Average Profit %"] = last_df_prof_perc.mean(axis=1)

        if st.checkbox('Profit graph'):
            #st.write(last_df_prof)
            fig1 = last_df_prof.plot()
            st.plotly_chart(fig1)

        if st.checkbox('%Profit graph'):
            fig2 = last_df_prof_perc.plot()
            st.plotly_chart(fig2)

