#!/usr/local/bin/python2.7
# encoding: utf-8

import argparse
import os.path
import sys
import traceback

sys.path.insert(1,'.')

import grizzle
import sweattrails.device.fitparse
import sweattrails.device.fitparse.records


class FITAnalyzer(object):
    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('file', type=str, nargs='+',
                            help="File(s) to analyze")
        parser.add_argument("-q", "--quiet", action="store_true",
                            help="Silently analyze files, only reporting errors")
        parser.add_argument("-d", "--defs_only", action="store_true",
                            help="Only show definition records")
        parser.add_argument("-f", "--filter", type=int, action="append",
                            help="Only show records with the given number. Can be specified multiple times.");
        args = parser.parse_args()
        self.quiet = args.quiet
        self.defs_only = args.defs_only
        self.filter = args.filter
        self.filenames = [ f for f in args.file if os.path.exists(f) ]

    def analyze(self):
        for f in self.filenames:
            self._analyze(f)
        return 0
    
    def _print_def_record(self, rec):
        if self.filter and not rec.num in self.filter:
            return
        print ("DEF  %d. #%d: %s (%d entries) " % (self.record_number, rec.num, rec.name, len(rec.fields))).ljust(60, '-')
        for field in rec.fields:
            print "%s [%s]" % (field.name, field.type.name)
        print
            
    def _print_data_record(self, rec):
        if self.filter and not rec.num in self.filter:
            return
        if not self.defs_only:
            print ("DATA %d. #%d: %s (%d entries) " % (self.record_number, rec.num, rec.type.name, len(rec.fields))).ljust(60, '-')
            for field in rec.fields:
                to_print = "%s [%s]: %s" % (field.name, field.type.name, field.data)
                if field.data is not None and field.units:
                    to_print += " [%s]" % field.units
                print to_print
            print
            
    def _print_record(self, rec):
        self.record_number += 1
        if isinstance(rec, sweattrails.device.fitparse.records.DataRecord):
            self._print_data_record(rec)
        elif isinstance(rec, sweattrails.device.fitparse.records.DefinitionRecord):
            self._print_def_record(rec)

    def _analyze(self, f):
        if self.quiet:
            print f
        else:
            print ('##### %s ' % f).ljust(60, '#')
    
        print_hook_func = None
        if not self.quiet:
            print_hook_func = self._print_record
    
        self.record_number = 0
        a = sweattrails.device.fitparse.Activity(f)
        try:
            a.parse(hook_func = print_hook_func, hook_definitions = True)
        except sweattrails.device.fitparse.FitParseError as fpe:
            exc_type, exc_value, exc_traceback = fpe.exc_info
            if exc_value:
                traceback.print_exception(exc_type, exc_value, exc_traceback)
            
if __name__ == "__main__":
    analyzer = FITAnalyzer()
    sys.exit(analyzer.analyze())

