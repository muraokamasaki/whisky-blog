from flask import current_app


def insert_mapping(index):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.indices.create(index=index, ignore=400, body={
        'mappings': {
            'properties': {
                'score': {'type': 'integer'},
                'timestamp': {'type': 'date'},
                'nose': {'type': 'text'},
                'palate': {'type': 'text'},
                'finish': {'type': 'text'},
                'distillery_': {'type': 'text'},
                'whisky_': {'type': 'text'},
                'tags_': {'type': 'keyword'},
                'user_': {'type': 'keyword'}
            }
        }
    })


def delete_mapping(index):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.indices.delete(index=index)


def get_mappings():
    if not current_app.elasticsearch:
        return
    return current_app.elasticsearch.indices.get_mapping(index='_all')


def add_doc_to_index(index, doc):
    if not current_app.elasticsearch:
        return
    body = {}
    for field in doc.searchable_fields:
        body[field] = getattr(doc, field)
    current_app.elasticsearch.index(index=index, id=doc.id, body=body)


def remove_doc_from_index(index, doc):
    if not current_app.elasticsearch:
        return
    current_app.elasticsearch.delete(index=index, id=doc.id)


# Use a bool filter to combine the matches of `query`, the exclusion of `excluded` and filtered by `tags`.
def query_index(index, query, excluded, tags, offset, size, sort):
    if not current_app.elasticsearch:
        return [], 0
    sort_order = {'rel': '_score', 'old': {'timestamp': 'asc'}, 'new': {'timestamp': 'desc'}}
    search = current_app.elasticsearch.search(
        index=index, body={
            'query': {
                'bool': {
                    'must': [{
                        'multi_match': {
                            'query': query,
                            'fields': ['*'],
                            'lenient': 'true'
                        }
                    }] if query else [],
                    'must_not': [{
                        'multi_match': {
                            'query': excluded,
                            'fields': ['*'],
                            'lenient': 'true'
                        }
                    }] if excluded else [],
                    'filter': [{
                        'term': {
                            'tags_': t
                        }
                    } for t in tags]
                }
            },
            'from': (offset - 1) * size, 'size': size, 'sort': sort_order[sort] if sort else '_score'
        }
    )
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']


def query_advanced(index, review, score_lower, score_greater, tags, whisky, user, offset, size, sort='_score'):
    if not current_app.elasticsearch:
        return [], 0
    sort_order = {'rel': '_score', 'old': {'timestamp': 'asc'}, 'new': {'timestamp': 'desc'}}
    body_must = []
    body_should = []
    body_filter = []
    if review:
        body_must.append({
            'multi_match': {
                'query': review,
                'fields': ['nose', 'palate', 'finish'],
                'type': 'most_fields'
            }
        })
    if score_lower or score_greater:
        body_filter.append({
            'range': {
                'score': {
                    'lte': score_greater if score_greater else 100,
                    'gte': score_lower if score_lower else 0
                }
            }
        })
    if user:
        body_filter.append({
            'term': {
                'user_': user
            }
        })
    if whisky:
        body_should.append({
            'match': {
                'distillery_': {
                    'query': whisky,
                    'fuzziness': 'AUTO'
                }
            }
        })
        body_should.append({
            'match': {
                'whisky_': {
                    'query': whisky,
                    'fuzziness': 'AUTO',
                    'boost': 0.5  # whisky name has lower contribution to score
                }
            }
        })
    if tags:
        # tags form a sub-query that scores a review higher the more matching tags it contains
        body_should.append({
            'bool': {
                'should': [{
                    'term': {
                        'tags_': t
                    }
                } for t in tags]
            }
        })
    search = current_app.elasticsearch.search(
        index=index, body={
            'query': {
                'bool': {
                    'must': body_must,
                    'should': body_should,
                    'filter': body_filter,
                    'minimum_should_match': 1 if body_should else 0,
                    'boost': 2
                }
            },
            'from': (offset - 1) * size, 'size': size, 'sort': sort_order[sort] if sort else '_score'
        }
    )
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']
