# -*- coding: utf-8 -*-

from models import UserRole, FallenApp
import base64, _strptime, datetime
from settings import TIMEFORMAT

def create_entity_by_name(entity_cls, entity_name):
    """Create an entity in the DB by with gevin name
        but first verifies if it doesn't exist already.
        Created or retrieved entity is returned back 
        to a caller.
    """
    if not entity_cls.all().filter("name =", entity_name).get():
        instance = entity_cls(name=entity_name)
        instance.put()
        return instance

def create_role_if_doesnt_exist(role_name):
    return create_entity_by_name(UserRole, role_name)

def create_app_model_if_doesnt_exist(app_name):
    return create_entity_by_name(FallenApp, app_name)

def copy_obj_with_changes(original, delete_original=True, **extra_args):
    """Originaly this function was aimed to change a parent for 
        an entity. But in proccess of creating the decision was
        made to expand a field of applicating.

        Now it copies fields from original to a new entity and
        then deletes the original entity unless it's said not 
        to do it. You can pass parameter parent to change it in
        a new entity.

        Params:
        original: the entity to copy/move
        delete_original: boolean parameter to define whether to delete
            the original entity or not (default value is True)
        extra_args: Keyword arguments to override from the cloned 
            entity and pass to the constructor.

        Returns:
        A cloned, possibly modified, copy of entity original.
    """

    klass = original.__class__
    props = dict((k, v.__get__(original, klass)) for k, v in klass.properties().iteritems())
    props.update(extra_args)

    new_entity = klass(**props)
    if delete_original: original.delete()
    new_entity.put()

    return new_entity

def set_or_default(target, value):
    if value:
        target = value

def give_next_page(query, bookmark=None, page_size=50):
    bookmark_date = None
    
    if bookmark: # It is base64 datetime string
        bookmark_date = datetime.datetime.strptime(base64.b64decode(bookmark), TIMEFORMAT) 
        query.filter('created <=', bookmark_date)
    query.order('-created')                        
    entities = query.fetch(page_size+1)

    next_link = None # see next conditional statement, next_link can be changed
    previous_link = base64.b64encode(bookmark_date.strftime(TIMEFORMAT)) if bookmark_date else None

    if len(entities) == page_size + 1:
        next_link = base64.b64encode(entities[-1].created.strftime(TIMEFORMAT))
        entities = entities[:page_size]

    template_values = {}
    template_values['next'] = next_link
    template_values['previous'] = previous_link
    template_values['entities'] = entities

    return template_values

def give_previous_page(query, bookmark=None, page_size=50):
    bookmark_date = datetime.datetime.strptime(base64.b64decode(bookmark), TIMEFORMAT) 
    query.filter('created >', bookmark_date)
    query.order('created')                        
    entities = query.fetch(page_size+1)

    next_link = base64.b64encode(bookmark_date.strftime(TIMEFORMAT)) if bookmark_date else None 
    previous_link = None # see next conditional statement, previous_link can be changed

    if len(entities) == page_size + 1:
        entities = entities[:page_size]
        previous_link = base64.b64encode(entities[-1].created.strftime(TIMEFORMAT))

    # always reverse a list of entities
    entities.reverse()

    template_values = {}
    template_values['next'] = next_link
    template_values['previous'] = previous_link
    template_values['entities'] = entities

    return template_values

def give_a_page(entity_cls, next=None, previous=None, parent=None, page_size=50):
    query = entity_cls.all()
    if parent:
        query.ancestor(parent)

    if previous:
        return give_previous_page(query, previous, page_size)
    else:
        return give_next_page(query, next, page_size)