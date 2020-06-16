import numpy as np
import os

import jinja2
import bokeh
import bokeh.plotting as bk
from bokeh.embed import components
from bokeh.models import ColumnDataSource

from ..plots.nightlyqa import find_night, get_timeseries, plot_timeseries, get_nightlytable, get_moonloc, get_skypathplot, overlaid_hist, overlaid_hist_fine, get_exptype_counts, plot_timeseries_fine

def get_nightlyqa_html(night, exposures, fine_data, tiles, outdir, link_dict, height=250, width=250):
    '''docstring'''
    
    summary_str = "summaryqa.html"
    last_str = link_dict['last']
    first_str = link_dict['first']
    night_links = link_dict['n{}'.format(night)]
    next_str = night_links['next']
    prev_str = night_links['prev']

    #- Separate calibration exposures
    all_exposures = exposures[exposures['PROGRAM'] != 'CALIB']
    all_calibs = exposures[exposures['PROGRAM'] == 'CALIB']

    #- Filter exposures to just this night and adds columns DATETIME and MJD_hour
    exposures = find_night(all_exposures, night)
    calibs = find_night(all_calibs, night)
    night_fine_data = find_night(fine_data, night)

    #- Plot options
    #title='Airmass, Seeing, Exptime vs. Time for {}/{}/{}'.format(night[4:6], night[6:], night[:4])
    TOOLS = ['box_zoom', 'reset', 'wheel_zoom']
    TOOLTIPS = [("EXPID", "@EXPID"), ("Exposure Time", "@EXPTIME"), ("Airmass", "@AIRMASS"), 
                ("Seeing", "@SEEING"), ("Transparency", "@TRANSP"), ('Hour Angle', '@HOURANGLE')]
    
    #- Create ColumnDataSource for linking timeseries plots
    COLS = ['EXPID', 'TIME', 'AIRMASS', 'SEEING', 'EXPTIME', 'TRANSP', 'SKY', 'HOURANGLE']
    fine_COLS = ['EXPID', 'TIME', 'AIRMASS', 'SEEING', 'TRANSP', 'SKY', 'HOURANGLE']
    exp_src = ColumnDataSource(data={c:np.array(exposures[c]) for c in COLS})
    fine_src = ColumnDataSource(data={c:np.array(night_fine_data[c]) for c in fine_COLS})

    #- Get timeseries plots for several variables
    min_border_right_time = 0
    min_border_left_time = 60
    min_border_right_hist = 0
    min_border_left_hist = 70
    min_border_right_count = 0
    min_border_left_count = 70
    min_border_right_sky = 0
    min_border_left_sky = 60

    time_hist_plot_height = 160
    
    airmass = plot_timeseries_fine(fine_src, exp_src, 'AIRMASS', 'green', tools=TOOLS, x_range=None, title=None, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    
    seeing = plot_timeseries_fine(fine_src, exp_src, 'SEEING', 'navy', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    
    transp = plot_timeseries_fine(fine_src, exp_src, 'TRANSP', 'purple', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    
    hourangle = plot_timeseries_fine(fine_src, exp_src, 'HOURANGLE', 'maroon', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    
    brightness = plot_timeseries_fine(fine_src, exp_src, 'SKY', 'pink', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)
    
    exptime = plot_timeseries(exp_src, 'EXPTIME', 'darkorange', tools=TOOLS, x_range=airmass.x_range, tooltips=TOOLTIPS, width=600, height=time_hist_plot_height, min_border_left=min_border_left_time, min_border_right=min_border_right_time)

    #- Convert these to the components to include in the HTML
    timeseries_script, timeseries_div = components(bk.Column(exptime, airmass, seeing, transp, hourangle, brightness))

    #making the nightly table of values
    nightlytable = get_nightlytable(exposures)
    table_script, table_div = components(nightlytable)

    #adding in the skyplot components
    #skypathplot = get_skypathplot(exposures, tiles, width=600, height=250, min_border_left=min_border_left_sky, min_border_right=min_border_right_sky)
    #skypathplot_script, skypathplot_div = components(skypathplot)

    #adding in the components of the exposure types bar plot
    #exptypecounts = get_exptype_counts(exposures, calibs, width=250, height=250, min_border_left=min_border_left_count, min_border_right=min_border_right_count)
    #exptypecounts_script, exptypecounts_div = components(exptypecounts)

    #- Get overlaid histograms for several variables
    airmasshist = overlaid_hist_fine(fine_data, night_fine_data, 'AIRMASS', 'green', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    
    seeinghist = overlaid_hist_fine(fine_data, night_fine_data, 'SEEING', 'navy', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    
    transphist = overlaid_hist_fine(fine_data, night_fine_data, 'TRANSP', 'purple', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    
    hourangle = overlaid_hist_fine(fine_data, night_fine_data, "HOURANGLE", "maroon", 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    
    brightnesshist = overlaid_hist_fine(fine_data, night_fine_data, 'SKY', 'pink', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)
    
    exptimehist = overlaid_hist(all_exposures, exposures, 'EXPTIME', 'darkorange', 250, time_hist_plot_height, min_border_left=min_border_left_hist, min_border_right=min_border_right_hist)

    #adding in the components of the overlaid histograms
    overlaidhists_script, overlaidhists_div = components(bk.Column(exptimehist, airmasshist, seeinghist, transphist, hourangle, brightnesshist))
    
    env = jinja2.Environment(
        loader=jinja2.PackageLoader('nightwatch.webpages', 'templates')
    )
    
    template = env.get_template('nightlyqa.html')
    
    html_components = dict(
        bokeh_version=bokeh.__version__, night=night, summary_str = summary_str,
        next_str = next_str, prev_str = prev_str, first_str = first_str, last_str = last_str,
        #skypathplot_script=skypathplot_script, skypathplot_div=skypathplot_div,
        #exptypecounts_script=exptypecounts_script, exptypecounts_div=exptypecounts_div,
        timeseries_script=timeseries_script, timeseries_div=timeseries_div,
        overlaidhists_script=overlaidhists_script, overlaidhists_div=overlaidhists_div,
        table_script=table_script, table_div=table_div,
        )
    
     #- Combine template + components -> HTML
    html = template.render(**html_components)

    #- Write HTML text to the output file
    outfile = os.path.join(outdir, 'nightqa-{}.html'.format(night))
    
    with open(outfile, 'w') as fx:
        fx.write(html)
    
    print('Wrote {}'.format(outfile))

    return html_components