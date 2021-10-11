# deriva-datapackage

This is a python package which facilitates querying the data contained in an offline datapackage as one would a public DERIVA catalog using deriva-py after that catalog were deployed *with* the datapackage. Thus we allow you to test queries that could be executed in production using deriva-py query syntax. Not all features are supported, more may be added as needed.

This library is most often used for constructing isomorphic FAIR assessments which can operate on offline datapackages instead of online in production.

## Installation

```bash
pip3 install git+https://github.com/nih-cfde/deriva-datapackage.git
```

## Usage

```python
from deriva_datapackage import create_offline_client
offline_client = create_offline_client('path/to/datapackage.json')

from deriva_datapackage import create_online_client
online_client = create_online_client('https://my_public_deriva_catalog/#1/public')

# both online_client and offline_client can be operated using the ERMRest DataPath query language
for client in (offline_client, online_client):
  p = client.tables['file'].filter(client.tables['file'].id == 'myid')
  p = p.link(client.tables['file_fk'])
  print(client, p.entities())
```

For more information about DataPath, see <http://docs.derivacloud.org/deriva-py/README.html>.
