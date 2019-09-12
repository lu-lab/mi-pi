#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import datetime
import os.path
import pickle
from googleapiclient.discovery import build
from kivy.logger import Logger
from googleapiclient.errors import HttpError
import gc
import socket


class SheetsTransferData:

    def __init__(self, spreadsheet_id, system_id, paired_system_id, param_col_dict, data_col_dict, time_res_cell,
                 led_dosage_cell, experiment_code, start_row=5):
        self.scopes = 'https://www.googleapis.com/auth/spreadsheets'
        self.spreadsheet_id = spreadsheet_id
        # assume the range is the whole spreadsheet
        self.spreadsheet_range = '-'.join([system_id, 'parameters'])
        if paired_system_id is not None:
            self.paired_spreadsheet_range = '-'.join([paired_system_id, 'parameters'])
        else:
            Logger.info('Sheet: no paired system set')
        self.led_dosage_cell = led_dosage_cell
        self.creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
        if self.creds is None:
            Logger.info("Sheet: no token.pickle file available")
        self.start_row = start_row
        self.param_col_dict = param_col_dict
        self.param_to_col_mapping = self.alph_to_col(self.param_col_dict)
        self.data_col_dict = data_col_dict
        self.data_to_col_mapping = self.alph_to_col(self.data_col_dict)
        time_raw = self.read_sheet(cell_range=time_res_cell)
        time_list = time_raw[0][0].split(':')

        # write experiment code to spreadsheet
        values = [
            [
                experiment_code
            ],
        ]
        body = {'values': values}
        self.write_sheet(body, cell_range='B1')

        # compute time resolution in seconds
        self.time_res = int(float(time_list[0]))*3600 + int(float(time_list[1]))*60 + int(float(time_list[2]))
        Logger.info('Sheet: Time resolution is %s' % self.time_res)

    def alph_to_col(self, dict):
        col_dict = dict.copy()
        for (k, v) in col_dict.items():
            col_dict[k] = ord(v.lower())-97
        return col_dict

    def clear_data(self, column):
        # clear data from the specified column (excluding headers) off of the spreadsheet
        clear_range = column + str(self.start_row) + ':' + column
        spreadsheet_range = self.spreadsheet_range + '!' + clear_range
        body = {}
        success = False
        counter = 0
        while not success and counter < 4:
            try:
                # build the service
                service = build('sheets', 'v4', credentials=self.creds)
                response = service.spreadsheets().values().clear(spreadsheetId=self.spreadsheet_id,
                                                                 range=spreadsheet_range, body=body)\
                                                          .execute()
                Logger.debug('Sheets: column %s cleared')
                success = True
            except HttpError as err:
                # If the error is a rate limit or connection error,
                # wait and try again.
                if err.resp.status in [403, 500, 503]:
                    time.sleep(5)
            except socket.timeout:
                time.sleep(5)
            finally:
                counter += 1
        gc.collect()

    def init_time(self, cell_range='A5'):
        timestr = time.strftime("%Y/%m/%d %H:%M:%S")
        values = [
            [
                # Cell values ...
                timestr
            ],
            # Additional rows ...
        ]
        body = {
            'values': values
        }
        self.write_sheet(body, cell_range=cell_range)
        return datetime.datetime.strptime(timestr, "%Y/%m/%d %H:%M:%S")

    def get_params(self, cur_row):
        cell_range = str(cur_row) + ':' + str(cur_row)
        values = self.read_sheet(cell_range=cell_range)
        if not values:
            Logger.info('No data found. Make sure your google sheet is populated with data')
            return None, False
        else:
            # return
            params = self.param_to_col_mapping.copy()
            for (k, v) in params.items():
                if len(values[0]) > v:
                    params[k] = values[0][self.param_to_col_mapping[k]]
            return params, True

    def read_sheet(self, **kwargs):
        allowed_keys = ['cell_range', 'spreadsheet_tab']
        if kwargs is not None:
            self.__dict__.update((key, value) for (key, value) in kwargs.items() if key in allowed_keys)

        if hasattr(self, 'spreadsheet_tab'):
            if hasattr(self, 'cell_range'):
                spreadsheet_range = self.spreadsheet_tab + '!' + self.cell_range
            else:
                spreadsheet_range = self.spreadsheet_tab
        else:
            if hasattr(self, 'cell_range'):
                spreadsheet_range = self.spreadsheet_range + '!' + self.cell_range
            else:
                spreadsheet_range = self.spreadsheet_range

        success = False
        counter = 0
        while not success and counter < 4:
            try:
                #build the service
                service = build('sheets', 'v4', credentials=self.creds)
                # Call the Sheets API, checking for errors
                result = service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id,
                                                             range=spreadsheet_range).execute()
                values = result.get('values', [])
                success = True
            except HttpError as err:
                # If the error is a rate limit or connection error,
                # wait and try again.
                if err.resp.status in [403, 500, 503]:
                    time.sleep(5)
                values = []
            except socket.timeout:
                time.sleep(5)
                values = []
            counter += 1
        gc.collect()
        return values

    def write_sheet(self, body, **kwargs):
        allowed_keys = ['cell_range']
        if kwargs is not None:
            self.__dict__.update((key, value) for (key, value) in kwargs.items() if key in allowed_keys)

        if hasattr(self, 'cell_range'):
            spreadsheet_range = self.spreadsheet_range + '!' + self.cell_range
        else:
            spreadsheet_range = self.spreadsheet_range

        success = False
        counter = 0
        while not success and counter < 4:
            try:
                # build the service
                service = build('sheets', 'v4', credentials=self.creds)
                result = service.spreadsheets().values().update(
                    spreadsheetId=self.spreadsheet_id, range=spreadsheet_range,
                    valueInputOption="USER_ENTERED", body=body).execute()
                success = True
            except HttpError as err:
                # If the error is a rate limit or connection error,
                # wait and try again.
                if err.resp.status in [403, 500, 503]:
                    time.sleep(5)
            except socket.timeout:
                time.sleep(5)
            counter += 1
        gc.collect()
