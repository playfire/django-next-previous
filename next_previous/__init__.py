from itertools import islice, chain, repeat

from django.db.models import Q

class NextPreviousMixin(object):
    """
    Django model mixin factory that allows easy retrieval of the "next" and
    "previous" object(s) relative to the ordering specified in the model's
    ``ordering``.

    Care should be taken when adding indices for this query; a consistent
    ordering is achieved by the appending the primary key to all queries and
    the usage of both '>' and '<' and ascending and descending orderings may
    not be suitable for BTREE indices.

    The set over which the next and previous objects ranges can be restricted
    to to provide "the next message by this user"-type semantics::

        class Message(models.Models, NextPreviousMixin):
            user = model.ForeignKey(User)
            content = models.CharField(max_length=140)
            created = models.DateTimeFeild(default=datetime.datetime.utcnow)

            class Meta:
                ordering = ('created',)

            def next_previous_filter(self, qs):
                return qs.filter(user=self.user_id)
    """

    def _cached_get_next_or_previous(self, next, num=1, **kwargs):
        cache_name = '_%s_items_cache' % ('next' if next else 'previous')
        cached = getattr(self, cache_name, None)
        if cached:
            cached_num, cached_results = cached
            if num <= cached_num:
                return cached_results[:num]

        out = self._get_next_or_previous(next, num, **kwargs)
        setattr(self, cache_name, (num, out))
        return out

    def _get_next_or_previous(self, next, num=1, **kwargs):
        fields = []
        operator = []

        for field in list(self._meta.ordering) + ['pk']:
            if field.startswith('-'):
                field = field[1:]
                op = next and 'lt' or 'gt'
            else:
                op = next and 'gt' or 'lt'

            if getattr(self, field, None) is None:
                # Value is None; we can't do field__lt=value lookups.
                continue

            fields.append(field)
            operator.append(op)

        # Construct Q such that any of:
        #
        #  (f_1 > self.f_1)
        #  (f_2 > self.f_2) & (f_1 = self.f_1)
        #  (f_3 > self.f_3) & (f_2 = self.f_2) & (f_1 = self.f_1)
        # ...
        #  (f_n > self.f_n) & (f_[n-1] = self.f_[n-1]) & ... & (f_1 = self.f_1)
        #
        # is true, replacing '>' where appropriate.
        q = Q()
        for idx in range(len(fields)):
            inner = Q(**{'%s__%s' % (fields[idx], operator[idx]): \
                getattr(self, fields[idx]),
            })
            for other in reversed(fields[:idx]):
                inner &= Q(**{other: getattr(self, other)})
            q |= inner

        qs = self.next_previous_filter(
            self.__class__._default_manager.all()
        ).filter(**kwargs).filter(q)

        if not next:
            qs = qs.reverse()

        return qs[:num]

    def _get_next_or_previous_single(self, num=1, **kwargs):
        val = self._cached_get_next_or_previous(num=num, **kwargs)

        if num == 1:
            try:
                return val[0]
            except IndexError:
                return None
        return val

    def next(self, **kwargs):
        """
        Returns the "next" object or objects relative to this model's
        ``ordering`` defined in its ``Meta`` class.

        If the keyword argument ``num`` is 1 (the default), this method will
        either return the next single object or ``None`` if there is no such
        object. Otherwise, this method will return a regular Django
        ``QuerySet`` with a maximum size of ``num``.

        Additional keyword arguments are opaque to ``NextPreviousMixin`` and
        are applied to a ``QuerySet.filter``.
        """
        return self._get_next_or_previous_single(next=True, **kwargs)

    def previous(self, **kwargs):
        """
        Returns the "previous" object or objects relative to this model's
        ``ordering`` defined in its ``Meta`` class.

        If the keyword argument ``num`` is 1 (the default), this method will
        either return the previous single object or ``None`` if there is no
        such object. Otherwise, this method will return a regular Django
        ``QuerySet`` with a maximum size of ``num``.

        Additional keyword arguments are opaque to ``NextPreviousMixin`` and
        are applied to a ``QuerySet.filter``.
        """
        return self._get_next_or_previous_single(next=False, **kwargs)

    def around(self, num=4, **kwargs):
        get = self._cached_get_next_or_previous
        prev = list(reversed(list(
            ipad(get(num=num, next=False, **kwargs), None, num)
        )))
        next = list(get(num=num, next=True, **kwargs))

        return prev + [self] + next

    def next_previous_filter(self, qs):
        return qs

def ipad(iterable, value, length):
    return islice(chain(iterable, repeat(value)), length)
