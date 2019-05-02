from flask import current_app


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


def query_index(index, query, excluded, offset, size):
    if not current_app.elasticsearch:
        return [], 0
    search = current_app.elasticsearch.search(
        index=index, body={
            'query': {
                'bool': {
                    'must': {
                        'multi_match': {'query': query, 'fields': ['*']}
                    },
                    'must_not': {
                        'multi_match': {'query': excluded, 'fields': ['*']}
                    }

                }
            },
            'from': (offset - 1) * size, 'size': size
        }
    )
    ids = [int(hit['_id']) for hit in search['hits']['hits']]
    return ids, search['hits']['total']['value']
