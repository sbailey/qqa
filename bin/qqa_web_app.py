import os, sys
import argparse
from flask import (Flask, send_from_directory)
from bokeh.resources import CDN
from bokeh.embed import file_html

app = Flask(__name__)
stat = ""
data = ""

parser = argparse.ArgumentParser(usage = "{prog} [options]")
parser.add_argument("-s", "--static", type=str, required=True, help="static file directory")
parser.add_argument("-d", "--data", type=str, help="data/fits file directory")
args = parser.parse_args()

stat = args.static
data = args.data

@app.route('/')
def redict_to_cal():
    print('redirecting to nights.html')
    return redirect('nights.html', code=302)


@app.route('/timeseries/')
def test_input():
    return """
    <html>
    <div>start date: <input type="number" id = "start"></div>
    <div>end date: <input type="number" id = "end"></div>
    <div>data column: <input id = "attribute"></div>
    <button onclick='
      var url = document.getElementById("start").value + "/" + document.getElementById("end").value + "/" +  document.getElementById("attribute").value
      window.open(url, "_top")
  '>Generate Timeseries</button>
    </html>
    """

@app.route('/timeseries/<int:start_date>/<int:end_date>/<string:attribute>')
def test_timeseries(start_date, end_date, attribute):
    from qqa.plots import timeseries
    figs = timeseries.generate_timeseries(data, start_date, end_date, attribute)

    if figs is None:
        return "No data between {} and {}".format(start_date, end_date)

    #bk.output_file(os.path.join(stat, "testing.html"), mode='inline')

    #bk.save(figs)
    #print('Wrote {}'.format(os.path.join(stat, "testing.html")))
    return file_html(figs, CDN, "{} between {} and {}".format(attribute, start_date, end_date))

@app.route('/<path:filepath>')
def getfile(filepath):
    global stat
    global data
    stat = os.path.abspath(stat)
    data = os.path.abspath(data)
    
    exists_html = os.path.isfile(os.path.join(stat, filepath))
    if exists_html:
        print("found " + os.path.join(stat, filepath), file=sys.stderr)
        print("retrieving " + os.path.join(stat, filepath), file=sys.stderr)
        return send_from_directory(stat, filepath)

    print("could NOT find " + os.path.join(stat, filepath), file=sys.stderr)

    # splits the url contents by '/'
    filedir, filename = os.path.split(filepath)

    filebasename, fileext = os.path.splitext(filename)

    splitname = filebasename.split('-')
    down = splitname.pop()
    if down[len(down)-1] != 'x':
        return 'no data for ' + os.path.join(stat, filepath)

    filebasename = '-'.join(splitname)
    fitsfilename = '{filebasename}.fits'.format(filebasename=filebasename)
    fitsfilepath = os.path.join(data, filedir, fitsfilename)
    exists_fits = os.path.isfile(fitsfilepath)

    exists_fits = os.path.isfile(fitsfilepath)
    if exists_fits:
        print("found " + fitsfilepath, file=sys.stderr)
        downsample = int(down[:len(down)-1])
        if downsample <= 0:
            return 'invalid downsample'

        # assume qqa/py is in PYTHONPATH
        # sys.path.append(os.path.abspath(os.path.join('..', 'py', 'qqa')))
        from qqa.webpages import plotimage

        plotimage.write_image_html(fitsfilepath, os.path.join(stat, filepath), downsample)
        return send_from_directory(stat, filepath)

    print("could NOT find " + fitsfilepath, file=sys.stderr)
    return 'no data for ' + os.path.join(stat, filepath)

if __name__ == "__main__":
    app.run(debug=True)
