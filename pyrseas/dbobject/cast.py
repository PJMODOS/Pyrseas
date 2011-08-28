# -*- coding: utf-8 -*-
"""
    pyrseas.cast
    ~~~~~~~~~~~~

    This module defines two classes: Cast derived from DbObject and
    CastDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObject, DbObjectDict


CONTEXTS = {'a': 'assignment', 'e': 'explicit', 'i': 'implicit'}
METHODS = {'f': 'function', 'i': 'inout', 'b': 'binary coercible'}


class Cast(DbObject):
    """A cast"""

    keylist = ['source', 'target']
    objtype = "CAST"

    def extern_key(self):
        """Return the key to be used in external maps for this cast

        :return: string
        """
        return '%s (%s AS %s)' % (self.objtype.lower(), self.source,
                                  self.target)

    def identifier(self):
        """Return a full identifier for a cast object

        :return: string
        """
        return "(%s AS %s)" % (self.source, self.target)

    def to_map(self):
        """Convert a cast to a YAML-suitable format

        :return: dictionary
        """
        dct = self.__dict__.copy()
        for k in self.keylist:
            del dct[k]
        dct['context'] = CONTEXTS[self.context]
        dct['method'] = METHODS[self.method]
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the cast

        :return: SQL statements
        """
        stmts = []
        with_clause = "\n    WITH"
        if hasattr(self, 'function'):
            with_clause += " FUNCTION %s" % self.function
        elif self.method == 'i':
            with_clause += " INOUT"
        else:
            with_clause += "OUT FUNCTION"
        as_clause = ''
        if self.context == 'a':
            as_clause = "\n    AS ASSIGNMENT"
        elif self.context == 'i':
            as_clause = "\n    AS IMPLICIT"
        stmts.append("CREATE CAST (%s AS %s)%s%s" % (
                self.source, self.target, with_clause, as_clause))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def diff_map(self, incast):
        """Generate SQL to transform an existing cast

        :param incast: a YAML map defining the new cast
        :return: list of SQL statements

        Compares the cast to an input cast and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        stmts.append(self.diff_description(incast))
        return stmts


class CastDict(DbObjectDict):
    "The collection of casts in a database"

    cls = Cast
    query = \
        """SELECT castsource::regtype AS source,
                  casttarget::regtype AS target,
                  CASE WHEN castmethod = 'f' THEN castfunc::regprocedure
                       ELSE NULL::regprocedure END AS function,
                  castcontext AS context, castmethod AS method,
                  description
           FROM pg_cast c
                JOIN pg_type s ON (castsource = s.oid)
                     JOIN pg_namespace sn ON (s.typnamespace = sn.oid)
                JOIN pg_type t ON (casttarget = t.oid)
                     JOIN pg_namespace tn ON (t.typnamespace = tn.oid)
                LEFT JOIN pg_proc p ON (castfunc = p.oid)
                     LEFT JOIN pg_namespace pn ON (p.pronamespace = pn.oid)
                LEFT JOIN pg_description d
                     ON (c.oid = d.objoid AND d.objsubid = 0)
           WHERE substring(sn.nspname for 3) != 'pg_'
              OR substring(tn.nspname for 3) != 'pg_'
              OR (castfunc != 0 AND substring(pn.nspname for 3) != 'pg_')
           ORDER BY castsource, casttarget"""

    query_83 = \
        """SELECT castsource::regtype AS source,
                  casttarget::regtype AS target,
                  CASE WHEN castfunc <> 0 THEN castfunc::regprocedure
                       ELSE NULL::regprocedure END AS function,
                  castcontext AS context,
                  CASE WHEN castfunc <> 0 THEN 'f'
                       ELSE 'b' END AS method,
                  description
           FROM pg_cast c
                JOIN pg_type s ON (castsource = s.oid)
                     JOIN pg_namespace sn ON (s.typnamespace = sn.oid)
                JOIN pg_type t ON (casttarget = t.oid)
                     JOIN pg_namespace tn ON (t.typnamespace = tn.oid)
                LEFT JOIN pg_proc p ON (castfunc = p.oid)
                     LEFT JOIN pg_namespace pn ON (p.pronamespace = pn.oid)
                LEFT JOIN pg_description d
                     ON (c.oid = d.objoid AND d.objsubid = 0)
           WHERE substring(sn.nspname for 3) != 'pg_'
              OR substring(tn.nspname for 3) != 'pg_'
              OR (castfunc != 0 AND substring(pn.nspname for 3) != 'pg_')
           ORDER BY castsource, casttarget"""

    def _from_catalog(self):
        """Use different query for older pg versions
        """
        if self.dbconn.version < 84000:
            self.query = self.query_83
        return DbObjectDict._from_catalog(self)

    def to_map(self):
        """Convert the cast dictionary to a regular dictionary

        :return: dictionary

        Invokes the `to_map` method of each cast to construct a
        dictionary of casts.
        """
        casts = {}
        for cst in self.keys():
            casts.update(self[cst].to_map())
        return casts

    def from_map(self, incasts, newdb):
        """Initalize the dictionary of casts by converting the input map

        :param incasts: YAML map defining the casts
        :param newdb: collection of dictionaries defining the database
        """
        for key in incasts.keys():
            if not key.startswith('cast (') or ' AS ' not in key.upper() \
                    or key[-1:] != ')':
                raise KeyError("Unrecognized object type: %s" % key)
            asloc = key.upper().find(' AS ')
            src = key[6:asloc]
            trg = key[asloc + 4:-1]
            incast = incasts[key]
            self[(src, trg)] = cast = Cast(source=src, target=trg)
            if not incast:
                raise ValueError("Cast '%s' has no specification" % key[5:])
            for attr, val in incast.items():
                setattr(cast, attr, val)
            if not hasattr(cast, 'context'):
                raise ValueError("Cast '%s' missing context" % key[5:])
            if not hasattr(cast, 'context'):
                raise ValueError("Cast '%s' missing method" % key[5:])
            cast.context = cast.context[:1].lower()
            cast.method = cast.method[:1].lower()
            if 'description' in incast:
                cast.description = incast['description']

    def diff_map(self, incasts):
        """Generate SQL to transform existing casts

        :param incasts: a YAML map defining the new casts
        :return: list of SQL statements

        Compares the existing cast definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the casts accordingly.
        """
        stmts = []
        # check input casts
        for (src, trg) in incasts.keys():
            incast = incasts[(src, trg)]
            # does it exist in the database?
            if (src, trg) not in self:
                # create new cast
                stmts.append(incast.create())
            else:
                # check cast objects
                stmts.append(self[(src, trg)].diff_map(incast))

        # check existing casts
        for (src, trg) in self.keys():
            cast = self[(src, trg)]
            # if missing, mark it for dropping
            if (src, trg) not in incasts:
                stmts.append(cast.drop())

        return stmts
