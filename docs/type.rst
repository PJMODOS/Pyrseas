Types and Domains
=================

.. module:: pyrseas.dbobject.dbtype

The :mod:`dbtype` module defines three classes, :class:`DbType`
derived from :class:`DbSchemaObject`, :class:`Domain` derived from
:class:`DbType`, and :class:`TypeDict` derived from and
:class:`DbObjectDict`.

Database Type
-------------

Class :class:`DbType` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a SQL type or
domain as defined in the PostgreSQL `pg_type` catalog. Note: Types are
not implemented yet.

.. autoclass:: DbType

Domain
------

:class:`Domain` is derived from :class:`~pyrseas.dbobject.DbType` and
represents a domain.

.. autoclass:: Domain

.. automethod:: Domain.to_map

.. automethod:: Domain.create

.. automethod:: Domain.diff_map

Type Dictionary
---------------

:class:`TypeDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of domains and enums in a database.

.. autoclass:: TypeDict

.. automethod:: TypeDict.from_map

.. automethod:: TypeDict.link_refs

.. automethod:: TypeDict.diff_map