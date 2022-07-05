from __future__ import annotations

from typing import List, Optional, Union, Type

from django.db import models
from django.forms import IntegerField


class CharacteristicType(models.IntegerChoices):
    """
    Типы характеристик:

    :param 0: - целое число (int)
    :param 1: - вещественное число (float)
    :param 2: - логическое значение (bool)
    :param 3: - строка (str)
    """

    int = 0, 'Целое число'
    float = 1, 'Вещественное число'
    bool = 2, 'Логическое значение'
    str = 3, 'Строка'

    @staticmethod
    def get_type_by_name(value_type: CharacteristicType) -> Type:
        """
        Возвращение типа по названию

        :param value_type: тип значение
        :return: наименование значения
        """
        if value_type not in CharacteristicType.values:
            raise TypeError('Неподдерживаемый тип данных')
        if value_type == 0:
            return int
        if value_type == 1:
            return float
        if value_type == 2:
            return bool
        return str

    @staticmethod
    def get_name_by_value(value: int | IntegerField) -> str:
        for choice in CharacteristicType.choices:
            if choice[0] == value:
                return choice[1]
        raise TypeError('Неподдерживаемый тип данных')


class ComparatorStrategy(models.IntegerChoices):
    """
    Стратегия сравнения

    0 - меньше - лучше (SMALLER)
    1 - больше - лучше (BIGGER)
    2 - по рейтингу (RATING)
    """
    SMALLER = 0, 'Меньше - лучше'
    BIGGER = 1, 'Больше - лучше'
    RATING = 2, 'По рейтингу'

    @staticmethod
    def get_comparator_type(strategy: ComparatorStrategy) -> Type:
        """
        Получение типа стратегии

        :param strategy: номер текущей стратегии
        :return: тип стратегия
        """
        strategies = {
            ComparatorStrategy.SMALLER: SmallerIsBetterComparator,
            ComparatorStrategy.BIGGER: BiggerIsBetterComparator,
            ComparatorStrategy.RATING: RatingComparator
        }

        return strategies[strategy]

    @staticmethod
    def get_name_by_value(value: int | IntegerField) -> str:
        for choice in ComparatorStrategy.choices:
            if choice[0] == value:
                return choice[1]
        raise TypeError('Неподдерживаемый тип компаратора')


class Characteristic:
    """
    Характеристики

    """
    def __init__(self, name: str, value_type: CharacteristicType, value: str):
        self.name = name
        self.type = value_type
        self.value = value

    def get_value(self) -> object:
        characteristic_type = CharacteristicType.get_type_by_name(self.type)
        return characteristic_type(self.value)

    def __check_name(self, other: Characteristic) -> None:
        if self.name != other.name:
            raise AttributeError('Нельзя сравнивать значения из различных характеристик')

    def __eq__(self, other: Characteristic) -> bool:
        self.__check_name(other)
        return self.get_value() == other.get_value()

    def __neq__(self, other: Characteristic) -> bool:
        return not self.__eq__(other)

    def __gt__(self, other: Characteristic) -> bool:
        self.__check_name(other)
        if self.type == CharacteristicType.str:
            raise ValueError('Нельзя использовать операции сравнения на строках. '
                             'Используйте RatingComparator')
        return self.get_value() > other.get_value()

    def __ge__(self, other: Characteristic) -> bool:
        return self.__gt__(other) or self.__ge__(other)

    def __lt__(self, other: Characteristic) -> bool:
        return not self.__gt__(other) and not self.__eq__(other)

    def __le__(self, other: Characteristic) -> bool:
        return self.__lt__(other) or self.__ge__(other)


class ComparatorResult:
    """
    Результат сравнения

    """
    def __init__(self,
                 better: Optional[Characteristic] = None,
                 worse: Optional[Characteristic] = None,
                 equal: Optional[List[Characteristic]] = None, cmp=0):
        """

        :param better: лучшее качество
        :param worse: худшее качество
        :param equal: одинаковые качества
        :param cmp:
        """
        ComparatorResult.clean(better, worse, equal)
        self.better = better
        self.worse = worse
        self.equal = equal
        self.cmp = cmp

    def __str__(self):
        return self.__class__.__name__

    @staticmethod
    def clean(better: Optional[Characteristic],
              worse: Optional[Characteristic],
              equal: Optional[List[Characteristic]]) -> None:
        cmp_filled: bool = better is not None and worse is not None
        equal_filled: bool = equal is not None
        if cmp_filled and equal_filled:
            raise AttributeError('Нельзя заполнить равные и неравные элементы в сравнении')
        if not cmp_filled and not equal_filled:
            raise AttributeError('Результаты сравнения не указаны')
        if equal_filled and len(equal) != 2:
            raise AttributeError('В списке equal должно быть ровно два объекта')


class Comparator:
    """
    Сравнение

    """
    def __init__(self, first: Characteristic, second: Characteristic):
        self.first = first
        self.second = second

    def __str__(self):
        return self.__class__.__name__

    def internal_compare(self) -> int:
        print(type(self))
        raise NotImplementedError('Не реализована функция сравнения в компараторе')

    def compare(self) -> ComparatorResult:
        cmp = self.internal_compare()
        if cmp > 0:
            return ComparatorResult(better=self.first, worse=self.second, equal=None, cmp=cmp)
        if cmp < 0:
            return ComparatorResult(better=self.second, worse=self.first, equal=None, cmp=cmp)
        return ComparatorResult(better=None, worse=None, equal=[self.first, self.second], cmp=cmp)


class RatingComparator(Comparator):
    """
    Сравнение рейтингов

    """
    def __init__(self,
                 first: Characteristic, second: Characteristic,
                 rating: List[dict[str, Union[str, int]]]
                 ):
        super().__init__(first, second)
        self.rating = rating
        self.rating_first = None
        self.rating_second = None

    def __str__(self):
        return self.__class__.__name__

    def get_rating(self, characteristic: Characteristic) -> int:
        for item in self.rating:
            if item['value'] == characteristic.value:
                return item['rating']
        raise ValueError('Указанное значение характеристики отсутствует в рейтинге')

    def internal_compare(self) -> int:
        self.rating_first = self.get_rating(self.first)
        self.rating_second = self.get_rating(self.second)
        if self.rating_first < self.rating_second:
            return 1
        if self.rating_first > self.rating_second:
            return -1
        return 0


class SmallerIsBetterComparator(Comparator):
    def __str__(self):
        return self.__class__.__name__

    def internal_compare(self) -> int:
        print(type(self))
        if self.first < self.second:
            return 1
        if self.first > self.second:
            return -1
        return 0


class BiggerIsBetterComparator(Comparator):
    def __str__(self):
        return self.__class__.__name__

    def internal_compare(self) -> int:
        if self.first > self.second:
            return 1
        if self.first < self.second:
            return -1
        return 0
