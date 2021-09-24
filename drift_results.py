# Container for drift result simulations
import calendar

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

import ais
import utils


class DriftResult:
    """
    Container for a drift result simulation.

    Arguments:
    ----------
    path: Path
        - Path to result files
    """
    def __init__(self, path):
        self.path = path

    def _get_starting_points(self, crs: str = 'epsg:4326', convert_lon: bool = True) -> pd.DataFrame:
        """Return starting points for simulation as GeoDataFrame.

        Notes:
        - Converts lon from [0, 360] to [-180, 180] if convert_lon is True
        """
        with xr.open_dataset(self.path) as ds:
            ds0 = ds.isel(time=0)

        df = ds0.to_dataframe()

        # Aleutian project uses [0, 360) instead of [-180, 180) to avoid dateline issues
        # - Convert back to [-180, 180)
        if convert_lon:
            df.lon = utils.lon360_to_lon180(df.lon)

        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(df.lon, df.lat)
        )
        return gdf.set_crs(crs)

    def _calc_pt(self, ais: ais.AIS, **kwargs) -> np.ndarray: 
        """Return GeoDataFrame Pt (probability of vessel at release point) for each particle."""
        # Get starting position of very particle (drifting vessel)
        starting_points = self._get_starting_points(**kwargs)
        locs = np.vstack((starting_points.lon.values, starting_points.lat.values)).T

        # Find vessel count in AIS data from starting positing
        _, ix = ais.tree.query(locs)
        starting_counts = ais.vessel_counts.iloc[ix].counts.values

        # Pt is probability that a vessel is at the release point for the month.
        # - If there were more vessels than days of the month, make Pt = 1
        ndays_in_month = calendar.monthrange(ais.date.year, ais.date.month)[1]
        pt = starting_counts / ndays_in_month
        pt[pt > 1] = 1

        return pt