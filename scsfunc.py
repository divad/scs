#!/usr/bin/python

import func_module

class ScsFunc(func_module.FuncModule):
	version = "0.1"
	api_version = "0.0.1"
	description = "SCS integration into the Fedora Unified Network Controller - Func"

	def self.echo(self):
		pass

	def self.time(self):
		pass

	def self.add(self, number1, number2):
		return number1 + number2
