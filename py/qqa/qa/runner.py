'''
QARunner class
'''

import os, sys
import json
import traceback
import glob

import numpy as np
import fitsio
from astropy.table import join, Table

import desiutil.log

from .amp import QAAmp
from .noisecorr import QANoiseCorr
from .specscore import QASpecscore
from .traceshift import QATraceShift
from .psf import QAPSF
from .fiberflat import QAFiberflat
# from .fibersnr import QAFiberSNR

class QARunner(object):

    #- class-level variable of default QA classes to run
    default_qalist = (QAAmp, QANoiseCorr, QASpecscore, QATraceShift, QAPSF,QAFiberflat)

    def __init__(self, qalist=None):
        '''TODO: document'''
        if qalist is None:
            qalist = QARunner.default_qalist

        #- Runner keeps instances, not just their classes
        self.qalist = [X() for X in qalist]

    def run(self, indir, outfile=None, json_gen=True):
        '''TODO: document'''
        log = desiutil.log.get_logger()
        log.debug('Running QA in {}'.format(indir))

        preprocfiles = sorted(glob.glob('{}/preproc-*.fits'.format(indir)))
        if len(preprocfiles) == 0:
            log.error('No preproc files found in {}'.format(indir))
            raise RuntimeError

        # We can have different flavors (signal+dark) with calibration data
        # obtained with a calibration slit hooked to a single spectrograph.
        # So we have to loop over all frames to check if there are science,
        # arc, or flat flavors as guessed by qproc.
        qframefiles = sorted(glob.glob('{}/qframe-*.fits'.format(indir)))
        if len(qframefiles) == 0 : # no qframe so it's either zero or dark
            hdr = fitsio.read_header(preprocfiles[0], 0)
            flavor = hdr['FLAVOR'].strip()
        else :
            flavor = None
            for qframefile in qframefiles : # look at all of them and prefer arc or flat over dark or zero
                hdr = fitsio.read_header(qframefile, 0)
                this_flavor = hdr['FLAVOR'].strip().upper()
                if this_flavor == "ARC" or this_flavor == "FLAT" :
                    flavor = this_flavor
                    # we use this so we exit the loop
                    break
                elif flavor == None :
                    flavor = this_flavor
                    # we stay in the loop in case another frame has another flavor


        log.debug('Found FLAVOR={} files'.format(flavor))

        results = dict()
        for qa in self.qalist:
            if qa.valid_flavor(flavor):
                log.debug('Running {} {}'.format(qa, qa.output_type))
                qa_results = None
                try:
                    qa_results = qa.run(indir)
                except Exception as err:
                    log.warning('{} failed on {} because {}; skipping'.format(qa, indir,str(err)))
                    exc_info = sys.exc_info()
                    traceback.print_exception(*exc_info)
                    del exc_info
                    #raise(err)
                    #- TODO: print traceback somewhere useful

                if qa_results is not None :
                    if qa.output_type not in results:
                        results[qa.output_type] = list()
                    results[qa.output_type].append(qa_results)

            else :
                log.debug('Skip {} {} for {}'.format(qa, qa.output_type, flavor))
        #- Combine results for different types of QA
        join_keys = dict(
            PER_AMP = ['NIGHT', 'EXPID', 'SPECTRO', 'CAM', 'AMP'],
            PER_CAMERA = ['NIGHT', 'EXPID', 'SPECTRO', 'CAM'],
            PER_FIBER = ['NIGHT', 'EXPID', 'SPECTRO', 'FIBER'],
            PER_CAMFIBER = ['NIGHT', 'EXPID', 'SPECTRO', 'CAM', 'FIBER'],
            PER_SPECTRO = ['NIGHT', 'EXPID', 'SPECTRO'],
            PER_EXP = ['NIGHT', 'EXPID'],
        )

        if json_gen:
            from pkg_resources import resource_filename
            jsonfiledir = resource_filename('qqa', os.path.join('cal_files', 'timeseries_dropdown.json'))
            if os.path.isdir(os.path.dirname(jsonfiledir)):
                with open(jsonfiledir, 'w') as out:
                    result1 = dict()
                    for key1 in results:
                        if key1 != "PER_CAMFIBER":
                            colnames_lst = results[key1][0].colnames
                            for i in join_keys[key1]:
                                colnames_lst.remove(i)
                            result1[key1] = colnames_lst
                    json.dump(result1, out)
                print('Wrote {}'.format(jsonfiledir))

        for qatype in list(results.keys()):
            if len(results[qatype]) == 1:
                results[qatype] = results[qatype][0]
            else:
                tx = results[qatype][0]
                for i in range(1, len(results[qatype])):
                    tx = join(tx, results[qatype][i], keys=join_keys[qatype], join_type='outer')
                results[qatype] = tx

            #- convert python string to bytes for FITS format compatibility
            if 'AMP' in results[qatype].colnames:
                results[qatype]['AMP'] = results[qatype]['AMP'].astype('S1')
            if 'CAM' in results[qatype].colnames:
                results[qatype]['CAM'] = results[qatype]['CAM'].astype('S1')

            #- TODO: NIGHT/EXPID/SPECTRO/FIBER int64 -> int32 or int16
            #- TODO: metrics from float64 -> float32

        if outfile is not None:
            for tx in results.values():
                night = tx['NIGHT'][0]
                expid = tx['EXPID'][0]
                break

            #- To do: consider propagating header from indir/desi*.fits.fz
            with fitsio.FITS(outfile, 'rw', clobber=True) as fx:
                fx.write(np.zeros(3, dtype=float), extname='PRIMARY', header=hdr)
                for qatype, qatable in results.items():
                    fx.write_table(qatable.as_array(), extname=qatype, header=hdr)

        return results
