class OnOff:
	def __init__(self, count: int = 4):
		self.max_count = count
		self.last = None
		self._reset()

	def _reset(self):
		self.zeros = 0
		self.positive = 0
		self.negative = 0

	def balance(self, recommended: int):
		if self.last is None:
			self.last = recommended
		else:
			change = False
			if (self.last == 0 and recommended == 0) or self.last * recommended > 0:
				change = True
			elif self.last == 0:
				if recommended > 0:
					self.positive += 1
					self.negative = 0
				else:
					self.negative += 1
					self.positive = 0
			elif self.last > 0:
				if recommended == 0:
					self.zeros += 1
				else:
					self.negative += 1
			else:
				if recommended == 0:
					self.zeros += 1
				else:
					self.positive += 1
			if self.zeros > self.max_count or self.positive > self.max_count or self.negative > self.max_count:
				change = True
			if change:
				self._reset()
				self.last = recommended
		return self.last
