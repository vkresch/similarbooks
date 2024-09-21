import pandas as pd
from sklearn.preprocessing import MinMaxScaler


class Scaler:
    def __init__(self):
        self._scaler = MinMaxScaler()
        self._colnames = None
        self._scale_dict = {}

    def scale(self, df):
        # call for training data
        self._colnames = df.columns
        self._scale_dict = {
            column: {"min": float(df[column].min()), "max": float(df[column].max())}
            for column in self._colnames
        }
        return pd.DataFrame(
            self._scaler.fit_transform(df), columns=df.columns, index=df.index
        )

    def unscale(self, df):
        return pd.DataFrame(
            self._scaler.inverse_transform(df), columns=df.columns, index=df.index
        )

    def __unscale(self, data, colname):
        matrix = data[colname]
        return (
            matrix
            * (self._scale_dict[colname]["max"] - self._scale_dict[colname]["min"])
        ) + self._scale_dict[colname]["min"]

    def unscale_matrix(self, data, colname):
        return self.__unscale(data, colname)

    def transform(self, df):
        # call for test data
        return pd.DataFrame(
            self._scaler.transform(df), columns=df.columns, index=df.index
        )

    @property
    def scale_dict(self):
        return self._scale_dict
