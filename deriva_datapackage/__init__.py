''' Client initializers for DERIVA online & offline clients
the offline client is DeirvaCompat, a compatible client interface
that can be instantiated from a datapackage by storing the data in
a local sqlalchemy database.
'''

import os
import sqlalchemy as sa
import sqlalchemy.orm as sa_orm

class DerivaCompat:
  def __call__(self):
    raise Exception('Call is not defined')

class DerivaCompatPrimitive(DerivaCompat):
  def __init__(self, value):
    self._value = value
  #
  def __call__(self):
    return self._value
  #
  def in_(self, other):
    return DerivaCompatPrimitive(
      self().in_(other() if isinstance(other, DerivaCompat) else other)
    )
  #
  def notin_(self, other):
    return DerivaCompatPrimitive(
      self().notin_(other() if isinstance(other, DerivaCompat) else other)
    )
  #
  def __eq__(self, other):
    return DerivaCompatPrimitive(
      self() == (other() if isinstance(other, DerivaCompat) else other)
    )
  #
  def __ne__(self, other):
    return DerivaCompatPrimitive(
      self() != (other() if isinstance(other, DerivaCompat) else other)
    )
  #
  def __and__(self, other):
    return DerivaCompatPrimitive(
      self() & (other() if isinstance(other, DerivaCompat) else other)
    )
  #
  def __or__(self, other):
    return DerivaCompatPrimitive(
      self() | (other() if isinstance(other, DerivaCompat) else other)
    )

class DerivaCompatQuery(DerivaCompat):
  def __init__(self, pkg, subj, query, path={}):
    self._pkg = pkg
    self._subj = subj
    self._query = query
    self._path = dict(path, **{ self._subj().name: self._subj.with_qs(self._query) })
    self.path = self
    for k, v in self._path.items():
      setattr(self, k, v)
  #
  def __call__(self):
    return self._query(self._pkg._sessionmaker.query(self._subj()))
  #
  def pivot(self, other):
    return DerivaCompatQuery(
      self._pkg,
      other,
      self._query,
      path=self._path,
    )
  #
  def link(self, other, on, join_type='left'):
    if join_type == 'left':
      q = lambda qs, _subj=self._subj, _query=self._query, _on=on: _query(qs).join(_subj(), _on())
    elif join_type == 'right':
      raise NotImplementedError
    elif join_type == 'full':
      q = lambda qs, _subj=self._subj, _query=self._query, _on=on: _query(qs).outerjoin(_subj(), _on())
    else:
      raise NotImplementedError
    #
    return DerivaCompatQuery(
      self._pkg,
      other,
      q,
      path=self._path,
    )
  #
  def filter(self, clause):
    return DerivaCompatQuery(
      self._pkg,
      self._subj,
      lambda qs, _query=self._query, _clause=clause: _query(qs).filter(_clause()),
      path=self._path,
    )
  #
  def groupby(self, *clauses):
    return DerivaCompatQuery(
      self._pkg,
      self._subj,
      lambda qs, _query=self._query, _clauses=clauses: _query(qs).group_by(*(_clause() for _clause in _clauses)),
      path=self._path,
    )
  #
  def entities(self):
    for record in self():
      yield {
        k: str(v)
        for k, v in record._asdict().items()
        if v
      }
  #
  def count(self):
    return self().count()

class DerivaCompatColumn(DerivaCompatPrimitive):
  def __init__(self, table, col):
    super().__init__(col)
    self._table = table
  #
  def __repr__(self):
    return f"{repr(self._table)}.{self._value.name}"

class DerivaCompatTable(DerivaCompat):
  def __init__(self, pkg, table, qs=None):
    super().__init__()
    self._pkg = pkg
    self._table = table
    self._qs = (lambda qs: qs) if qs is None else qs
    self.path = self
    self.column_definitions = {
      col.name: DerivaCompatColumn(self, col)
      for col in self._table.columns
    }
    for col in self._table.columns:
      setattr(self, col.name, self.column_definitions[col.name])
  #
  def __repr__(self):
    return f"table[{self._table.name}]"
  #
  def __call__(self):
    return self._table
  #
  def with_qs(self, qs):
    return DerivaCompatTable(
      self._pkg,
      self._table,
      lambda qs, _qs=qs, _query=self._qs: _qs(_query(qs))
    )
  #
  def alias(self, name):
    return DerivaCompatTable(
      self._pkg,
      self._table.alias(name),
      self._qs
    )
  #
  def _as_query(self):
    return DerivaCompatQuery(
      self._pkg,
      self,
      lambda qs, _query=self._qs: _query(qs)
    )
  #
  def link(self, other, on, join_type='left'):
    return self._as_query().link(other, on, join_type=join_type)
  #
  def filter(self, selector):
    return self._as_query().filter(selector)
  #
  def entities(self):
    if self._pkg._progress_bar:
      from tqdm import tqdm
      return tqdm(self._as_query().entities())
    else:
      return self._as_query().entities()
  #
  def count(self):
    return self._as_query().count()

class DerivaCompatPkg:
  def __init__(self, *pkgs, cachedir='.cached', progress_bar=False):
    self._progress_bar = progress_bar
    self.tables = {}
    # check_same_thread is safe here given that we don't ever write after init
    os.makedirs(cachedir, exist_ok=True)
    db = f"sqlite:///{cachedir.rstrip('/')}/datapackage.sqlite"
    # load data into sqlite
    for pkg in pkgs: pkg.index(db)
    self._engine = sa.create_engine(db)
    # auto-load schema into sqlalchemy metadata
    self._metadata = sa.MetaData()
    self._metadata.reflect(bind=self._engine)
    for resource_name, table in self._metadata.tables.items():
      self.tables[resource_name] = DerivaCompatTable(self, table)
    # setup sessionmaker
    self._sessionmaker = sa_orm.scoped_session(sa_orm.sessionmaker(bind=self._engine))

def DERIVA_col_in(qs, col, arr):
  '''
  DERIVA_col_in(Item, Item.col, [a, b, c])) => 
  Item.filter((Item.col == a | Item.col == b | Item.col == c))
  '''
  f = None
  for el in arr:
    if f is None:
      f = col == el
    else:
      f = f | (col == el)
  return qs if f is None else qs.filter(f)

def create_offline_client(*paths, cachedir='.cached', progress_bar=False):
  ''' Establish an offline client for more up to date assessments than those published
  '''
  from frictionless import Package
  return DerivaCompatPkg(*[Package(path) for path in paths], cachedir=cachedir, progress_bar=progress_bar)

def create_online_client(uri):
  ''' Create a client to access the public Deriva Catalog
  URI in the form: ${protocol}://${hostname}/chaise/recordset/#${record_number}/
  '''
  import re
  from urllib.parse import urlparse
  from deriva.core import ErmrestCatalog, get_credential
  uri_parsed = urlparse(uri)
  m = re.match(r'^(\d+)(/(.+))?$', uri_parsed.fragment)
  catalog_number = int(m.group(1))
  schema = m.group(3) or 'public'
  credential = get_credential(uri_parsed.hostname)
  catalog = ErmrestCatalog(uri_parsed.scheme, uri_parsed.hostname, catalog_number, credential)
  pb = catalog.getPathBuilder()
  return pb.schemas[schema]
