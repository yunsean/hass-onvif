#!/usr/bin/env python
#-*- coding:utf-8 -*-

import unittest
import base64

#from suds_passworddigest.token import UsernameDigestToken

class SudsTest(unittest.TestCase):
	def test_digest_generation(self):
		token = UsernameDigestToken()
		token.username = 'test'

		# case 1
		token.password = 'test'
		token.nonce = base64.decodebytes(b"8kqcOS9SFYxSRslITbBmlw==")
		token.created = "2012-10-29T08:18:34.836Z"

		self.assertEqual(token.generate_digest(),
			b"LOzA3VPv+2hFGOHq8O6gcEXsc/k=")


		# case 2
		token.password = 'ic3'
		token.nonce = base64.decodebytes(b"m4feQj9DG96uNY1tCoFBnA==")
		token.created = "2012-10-29T08:49:58.645Z"

		self.assertEqual(token.generate_digest(),
			b"K80tK4TyuvjuXvMu++O8twrXuTY=")

		# case 3
		token.password = 'wss22wert'
		token.nonce = base64.decodebytes(b"MzI2NjYyNzYxMQ==")
		token.created = "2012-10-29T05:39:24Z"

		self.assertEqual(token.generate_digest(),
			b"88FDZSIoCwQT9zhMqpcekDvZwVo=")

if __name__ == '__main__':
	unittest.main()
