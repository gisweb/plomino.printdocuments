# -*- coding: utf-8 -*-
from Products.CMFPlomino.PlominoUtils import json_dumps
import DateTime
import simplejson as json
from Products.CMFPlone.utils import safe_unicode
import os
import tempfile
from copy import deepcopy

try:
    from email.utils import parseaddr, formataddr
except ImportError:
    # BBB for python2.4 (Plone 3)
    from email.Utils import parseaddr, formataddr

from AccessControl import Unauthorized
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode
from Products.CMFPlomino.PlominoUtils import json_loads, json_dumps, DateToString, Now, open_url, DateTime

from Products.CMFPlone.utils import normalizeString
import simplejson as json
from .url_utils import Requests
import logging
import base64
from plone import api


_logger = logging.getLogger('plomino.printdocuments')

try:
    from zope.component.hooks import getSite
    # getSite
except ImportError:
    # BBB for Plone 3
    from zope.app.component.hooks import getSite
from zope.component import getMultiAdapter

DEFAULT_CHARSET = 'utf-8'



def is_json(s):
    try:
        json_loads(s)
    except ValueError:
        return False
    else:
        return True  

def getAttachmentInfo(doc, field=''):  
    result = list()   
    files_list = doc.getItem(field)
    if hasattr(files_list,'items'):
        for k, v in files_list.items():
            f = doc.getfile(k, asFile=True)
            if f:
                size = f.get_size()
                mime = f.getContentType()
                ext = k.split(".")[-1]
            # TODO select correct icon basing on mimetype
                file_info = dict(
                    name=k,
                    ext=ext,
                    mimetype=mime,
                    size=size,
                    url="%s/%s" % (doc.absolute_url(), k),
                    icon=f.getIcon(),
                    content=base64.b64encode(f.data)
                )
                result.append(file_info)

    return result
   
def getDatagridValue(doc,field='',form=''):
    
    db = doc.getParentDatabase()
    if form:
        frm = db.getForm(form)
    else:
        frm = doc.getForm()
    
    fld = frm.getFormField(field)

    if not fld or fld.FieldType != 'DATAGRID':
        return dict()
    elenco_fields = fld.getSettings().field_mapping  

    lista_fields = elenco_fields.split(',')
    diz_tot=[]
    associate_form = db.getForm(fld.getSettings().associated_form)

    for idx,itm in enumerate(doc.getItem(field)):
        diz = {}
        for k,v in enumerate(lista_fields):
            itemvalue = doc.getItem(field)[idx][k]            
            field_element = associate_form.getFormField(v)
            return doc            
            render_value = renderSimpleValue(doc,itemvalue,field_element,field_element.getFieldType())
            #return '%s %s %s %s %s' %(render_value,itemvalue,field_element,field_element.getFieldType(),type(itemvalue))
            diz[v] = render_value
            #diz[v] = doc.getItem(field)[idx][k]
        diz_tot.append(diz)
    return diz_tot

def getFieldValue(doc,field):   
    db = doc.getParentDatabase()
    form = doc.getForm()
    fld = form.getFormField(field)
    if fld != None:
        adapt = fld.getSettings()     
        fieldvalue = adapt.getFieldValue(form, doc)
        return fieldvalue 

def serializeGrid(doc,fieldName,formName='', render = True):    
    result = []    
    db = doc.getParentDatabase()
    datagridValue = doc.getItem(fieldName)
    if formName:
        form = db.getForm(formName)
    else:
        form = doc.getForm()
    if datagridValue:        
        #index_values = datagrid[int(index)]        
        field = form.getFormField(fieldName)   
 
        grid_form = db.getForm(field.getSettings().associated_form)
        grid_field_names = field.getSettings().field_mapping.split(',')        
        for row in datagridValue:
            result.append(dict([(k, renderSimpleItem(doc, v, grid_form.getFormField(k), render=render)) for k,v in zip(grid_field_names, row)]))
               
        #result['%s_%s' %(gridName,index)] = sub_result
    return result

def renderSimpleItem(doc, itemvalue, field, render=True):
    """ How simple item values are rendered """

    db = doc.getParentDatabase()
    renderedValue = None

    # if I need data representation (or metadata) for printing porposes
    try:
        fieldtype = field.getFieldType()
    except:
        fieldtype = 'TEXT'    
    if itemvalue and render and field:        
        if fieldtype == 'SELECTION':
            nfo = dict([i.split('|')[::-1] for i in field.getSettings().getSelectionList(doc)])
            if isinstance(itemvalue, basestring):
                renderedValue = nfo.get(itemvalue) or itemvalue
            else:
                renderedValue = [(nfo.get(i) or i) for i in itemvalue]

        # A COSA SERVIVA ???????????????
        # elif fieldtype not in ('TEXT', 'NUMBER', ):
        #     # not worth it to call the template to render text and numbers
        #     # it is an expensive operation
        #     fieldtemplate = db.getRenderingTemplate('%sFieldRead' % fieldtype) \
        #         or db.getRenderingTemplate('DefaultFieldRead')
        #     renderedValue = fieldtemplate(fieldname=name,
        #         fieldvalue = itemvalue,
        #         selection = field.getSettings().getSelectionList(doc),
        #         field = field,
        #         doc = doc
        #     ).strip()

    # try a guess
    if itemvalue and not field: 
        fieldtype = 'TEXT'
        
        # if isinstance(itemvalue, (int, float, )):
        #     fieldtype = 'NUMBER'
        # elif isinstance(itemvalue, DateTime):
        #     fieldtype = 'DATETIME'
        # else:
        #     fieldtype = 'TEXT'


    # if I need data value
    if renderedValue == None:
        if not itemvalue:
            renderedValue = ''
        elif fieldtype == 'TEXT':
            #renderedValue = safe_unicode(str(itemvalue)).encode('utf-8').decode('ascii', 'ignore')
            renderedValue = itemvalue.encode('utf-8')
        elif fieldtype == 'NUMBER':
            if render:
                custom_format = None if not field else field.getSettings('format')
                renderedValue = str(itemvalue) if not custom_format else custom_format % itemvalue
            else:
                renderedValue = itemvalue
        elif fieldtype == 'DATETIME':
            if field:
                custom_format = field.getSettings('format') or db.getDateTimeFormat()
            else:
                custom_format = db.getDateTimeFormat()
            try:
        
                renderedValue = itemvalue.strftime(custom_format)
            except:
                renderedValue = itemvalue

        else:
            # in order to prevent TypeError for unknown not JSON serializable objects
            try:
                json_dumps(itemvalue)
            except TypeError:
                renderedValue = u'%s' % itemvalue
            else:
                renderedValue = itemvalue

    return renderedValue


def serialDoc(doc, formid='', field_list=[], field_remove=[], render=True, follow_doclink=False):
    """
    Take a Plomino document :doc: and extract its data in a JSON-serializable
    structure for printing porposes.
    Item values are renderized according to the field definition and by default only
    defined fields will be considered.

    @param doc           : the PlominoDocument to serialize;
    @formid           : the name of the form used in serialization, if not use the associated form
    @param nest_datagrid : see serialItem;
    @param field_list    : if you need a subset of item to be serialized you can just
                           specify the list if item name you need;
    @param render        : see serialItem.
    """

    # bad_items are indistinguishable from good behaved citizen: they are unicode
    # values that just don't belong to the data (they are in fact metadata)
    # We want to skip those, and to do that we must explicitly list 'em

    db = doc.getParentDatabase()
    if formid != '':
        form = db.getForm(formid)
    else:
        form = doc.getForm()

    res = []
    if not form:
        _logger.info("la form %s non esiste" %formid)
        return res

    fieldlist = field_list or [i.id for i in form.getFormFields(includesubforms=True,
        doc=None, applyhidewhen=False) if i.getFieldType()!='DOCLINK' or follow_doclink]

    if field_remove:
        fieldlist = [i for i in fieldlist if i not in field_remove]
    

    #check field from item if not return data type
    for itemname in fieldlist:

        field = form.getFormField(itemname)
        itemvalue = doc.getItem(itemname)

        if field:
            fieldtype = field.getFieldType()
        else:
            field = None

        if fieldtype == 'DOCLINK':
            link_doc = db.getDocument(itemvalue)
            #!!!!!!!!!!!!!TODO!!!!!!!!!!!!!!!!!!
            res.append(itemname,serialDoc(doc=doc, serial_as=''))

        elif fieldtype == 'DATAGRID':
            grid_form = db.getForm(field.getSettings().associated_form)
            grid_field_names = field.getSettings().field_mapping.split(',')
            rows=list()
            dd = {}
            for row in itemvalue:
                #rows.append(dict([(k, renderSimpleItem(doc,v, grid_form.getFormField(k),render=render)) for k,v in zip(grid_field_names, row)]))
                for k,v in zip(grid_field_names, row):
                    grid_field = grid_form.getFormField(k)
                    grid_fieldtype = grid_field.getFieldType()
                    dd[k] = renderSimpleItem(doc,v, grid_field, render=render)
                    if render and grid_fieldtype == 'SELECTION':
                        dd[k + '_key'] = renderSimpleItem(doc,v, grid_field, render=False)
                rows.append(dd)
            res.append((itemname, rows))

        elif fieldtype in ['ATTACHMENT','UPLOAD']:
            #DA VEDERE CHE FARE
            boh=1

        else:
            adapt = field.getSettings()
            itemvalue = adapt.getFieldValue(form, doc, False)
            res.append((itemname, renderSimpleItem(doc,itemvalue,field,render=render)))
            #se restituisco i valori renderizzazi restituisco anche le chiavi
            if render and fieldtype == 'SELECTION':
                res.append((itemname + '_key', renderSimpleItem(doc,itemvalue,field,render=False)))


    return dict(res)

def getServiceConfiguration(doc,serviceName):
    portalProp = getToolByName(doc,'portal_properties')
    v1 = 'services_configuration'
    v2 = 'portal_properties'
    if 'services_configuration' in portalProp.keys():
        serviceConf = portalProp['services_configuration']
        v2 = v1
        v1 = serviceName
        for el in serviceConf.propertyItems():
            if el[0] == serviceName:
                return el[1]

    msg = 'ATTENZIONE! Attributo "%s" non trovato in %s.' % (v1,v2)
    _logger.info(msg)
    plone_tools = getToolByName(doc, 'plone_utils')
    plone_tools.addPortalMessage(msg, 'error')                


def getAttachmentFiles(doc, fieldName):
    
    docfolderId = doc.getId()
    dbfolderId = doc.getParentDatabase().id
    target = doc.portal_url.getPortalObject()[ATTACHMENT_FOLDER][dbfolderId][docfolderId]

    result = list()
    for fName in doc.getItem(fieldName, {}):
        if fName in target.keys():
            f = target[fName]
            file_info = dict(
                name = fName,
                mimetype = f.getContentType(),
                size = f.get_size(),
                url = f.absolute_url(),
                icon = f.getIcon(),
                b64file = base64.b64decode(f.get_data())
            )
            result.append(file_info)

    return result


def createDoc(doc, grp, model, field, redirect_url='', fieldsubset='', fieldsremove=''):
    """
    Create docx file from a PlominoDocument giving a model template

    model: model template name;
    grp: 
    field: field of the PlominDocument where to set the docx file created;
    redirect_url: where to redirect after this operation (optional)
    """

    
    if doc.portal_type != 'PlominoDocument':
        return ''    
    

    #URL del servizio di creazione del documento
    #wsUrl = get_property(doc,'ws_createdocx_URL').get('value')
    wsUrl = 'http://webservice.gisweb.vmserver/printservice/xCreate.php'
    
    #nome del progetto (da mettere in config o in qualche properties)
    project = 'savona'

    #cartella con i modelli (da mettere in config o in qualche properties)
    modelFolder = 'modelli'

    app = doc.getItem(APP_FIELD,'praticaweb')

    baseUrl = doc.portal_url.getPortalObject().absolute_url()
    modelUrl = "%s/%s/%s/%s/%s" %(baseUrl,modelFolder,app,grp,model)
    filename=model+'.docx' #TODO vedere x estensione

    # if """\\""" in filename:
    #     filename = filename.split("\\")[-1]
    # if """/""" in filename:
    #     filename = filename.split("/")[-1]    
    # filename = '.'.join(
    #         [normalizeString(s, encoding='utf-8') 
    #             for s in filename.split('.')])


    #Parametri della chiamata al servizio di creazione
    query = dict(
        project = project,
        app = app,
        group = grp,
        model = modelUrl,
        dataType = 'JSON',
        #mode = 'show',
        data = serialDoc(doc,fieldsubset,format='json'),
        id = doc.id,
        filename = filename,
        download = 'false'
    )
    

    #Creazione del documento tramite webservice
    plone_tools = getToolByName(doc.getParentDatabase().aq_inner, 'plone_utils')
    #plone_tools.addPortalMessage(json_dumps(query), 'message')

    try:
        r = requests_post(wsUrl, query, 'json', timeout=30)
    except Exception as error:    
        msg = ('%s: %s' % (type(error), error), 'error')
        plone_tools.addPortalMessage(*msg, request=doc.REQUEST)
        #doc.REQUEST.RESPONSE.redirect(doc.absolute_url())
    else:
        
        result = r['text']

        if is_json(result):
            res = json_loads(result)

            if res['success']==1:
                text = base64.b64decode(res['file'])

                doc.removeItem(field)
                (f,c) = doc.setfile(text,filename=filename,overwrite=True,contenttype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                if f and c:
                    doc.setItem(field, {f: c})
            else:
                msg = (res['message'], 'error')
                plone_tools.addPortalMessage(*msg, request=doc.REQUEST)
                #doc.REQUEST.RESPONSE.redirect(doc.absolute_url())
        else:
            if 'headers' in r.keys():
                h = get_headers(r['headers'])
                
                if h['content-type']=='application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                    doc.removeItem(field)
                    (f,c) = doc.setfile(result, filename=newfilename, overwrite=True, contenttype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    if f and c:
                        doc.setItem(file_type, {f: c})
                else:
                    msg = ('Risposta non di tipo DOCX', 'error')
                    plone_tools.addPortalMessage(*msg, request=doc.REQUEST)
                    #doc.REQUEST.RESPONSE.redirect(doc.absolute_url())
            else:
                msg = ('Il sistema ha risposto senza Header', 'error')
                plone_tools.addPortalMessage(*msg, request=doc.REQUEST)
                #doc.REQUEST.RESPONSE.redirect(doc.absolute_url())

        #if redirect_url:
            #doc.REQUEST.RESPONSE.redirect(redirect_url)




def convertToPdf(doc):
    if doc.portal_type != 'PlominoDocument':
        return ''
    if not file_type:
        return ''
    
    #URL del servizio di Conversione
    #serviceURL = doc.get_property('ws_converttopdf_URL').get('value')
    serviceURL=''
    
    files = doc.getItem(file_type, {})
    filename = files.keys()[-1]
    newfilename = filename.replace('.docx','.pdf').replace('.odt','.pdf')

    docurl='%s/%s' %(doc.absolute_url(),filename)

    url = '%s' %(serviceURL)
    query = dict(
        docurl = docurl
        )
    try:
       
        r = requests_post(url,query, 'json', timeout=30)
    except Exception as error:
        plone_tools = getToolByName(doc.getParentDatabase().aq_inner, 'plone_utils')
        msg = ""
        doc.setItem('test', msg)
        plone_tools.addPortalMessage(*msg, request=doc.REQUEST)
        doc.REQUEST.RESPONSE.redirect(doc.absolute_url())
    else:
        result = r['text']
        if is_json(result):
            res = json_loads(result)

            if res['success']==1:
                text = decode_b64(res['file'])

                doc.removeItem(file_type)
                (f,c) = doc.setfile(text,filename=newfilename,overwrite=True,contenttype='application/pdf')
                if f and c:
                    doc.setItem(file_type, {f: c})
                else:
                    msg = (res['message'], 'error')
                    plone_tools.addPortalMessage(*msg, request=doc.REQUEST)
                    doc.REQUEST.RESPONSE.redirect(doc.absolute_url())

def createPdf(doc):
    if doc.portal_type != 'PlominoDocument':
        return ''

    filename = '%s.pdf' % filename or \
        doc.REQUEST.get('filename') or \
        doc.getId()

    try:
        res = doc.restrictedTraverse('@@wkpdf').get_pdf_file()
    except Exception as err:        
        msg1 = "%s: %s" % (type(err), err)
        msg2 = u"Attenzione! Non e' stato possibile allegare il file: %s" % filename
        script.addPortalMessage(msg1, 'error')
        script.addPortalMessage(msg2, 'warning')
    else:
        (f,c) = doc.setfile(res,filename=filename,overwrite=overwrite,contenttype='application/pdf')
        if f and c:
            old_item = doc.getItem(itemname, {}) or {}
            old_item[filename] = c
            doc.setItem(itemname, old_item)








"""
####################### DOPPIONI DA RIVEDERE ########################

"""


#doppione???
def renderSimpleValue(doc,itemvalue,field,fieldtype=None):    
    db = doc.getParentDatabase()
    if not fieldtype:
        fieldtype = field.getFieldType()
    renderedValue = None
    if itemvalue and field:
        
        if fieldtype == 'SELECTION':                           
            nfo = dict([i.split('|')[::-1] for i in field.getSettings().getSelectionList(doc)])
            
            if isinstance(itemvalue, basestring):
                renderedValue = nfo.get(itemvalue) or itemvalue

            #elif isinstance(itemvalue[0], dict):
            #    renderedValue = [i.keys() for i in itemvalue]   

            else:
                renderedValue = [(nfo.get(i) or i) for i in itemvalue]


        elif fieldtype not in ('TEXT', 'NUMBER', ):
        # not worth it to call the template to render text and numbers
        # it is an expensive operation
            fieldtemplate = db.getRenderingTemplate('%sFieldRead' % fieldtype) \
                or db.getRenderingTemplate('DefaultFieldRead')
            renderedValue = fieldtemplate(fieldname=field.getId(),
                fieldvalue = itemvalue,
                selection = field.getSettings().getSelectionList(doc),
                field = field,
                doc = doc
            ).strip()    
             
    if renderedValue == None:
        if not itemvalue:
            renderedValue = ''
        elif fieldtype == 'TEXT':
            renderedValue = itemvalue
        elif fieldtype == 'NUMBER':
            custom_format = None if not field else field.getSettings('format')
            renderedValue = str(itemvalue) if not custom_format else custom_format % itemvalue
        elif fieldtype == 'DATETIME':
            if field:
                custom_format = field.getSettings('format') or db.getDateTimeFormat()
            else:
                custom_format = db.getDateTimeFormat()
            try:        
                renderedValue = itemvalue.strftime(custom_format)
            except:
                renderedValue = itemvalue
        else:
            try:
                json.dumps(itemvalue)
            except TypeError:
                renderedValue = u'%s' % itemvalue
            else:
                renderedValue = itemvalue
    return renderedValue    

def serialItem(doc, name, fieldnames = [],fieldsubset = [],fieldsremove=[]):

    
    db = doc.getParentDatabase()
    result = list()
    itemvalue = doc.getItem(name)
    if itemvalue == '':
        getFieldValue(doc,name)
    form = doc.getForm()


    if not fieldnames:
        fieldnames = [i.getId() for i in form.getFormFields(includesubforms=True, doc=None, applyhidewhen=False)]   
    if name in fieldnames:
        field = form.getFormField(name)     
        fieldtype = field.getFieldType()
    else:
        field = None
    if isinstance(itemvalue, (int, float, )):
        fieldtype = 'NUMBER'
    elif isinstance(itemvalue, DateTime):
        fieldtype = 'DATETIME'
    elif isinstance(itemvalue,list):
        fieldtype = 'SELECTION'
    else:
        fieldtype = 'TEXT'
    assert fieldtype, 'No fieldtype is specified for "%(name)s" with value "%(itemvalue)s"' % locals()     

    # arbitrary assumption
    if fieldtype == 'DATE':
        fieldtype = 'DATETIME'
    if fieldtype == 'DATAGRID' or (fieldtype == 'DOCLINK'):
        sub_result = list()
        if fieldtype == 'DATAGRID':
            grid_form = db.getForm(field.getSettings().associated_form)
            grid_field_names = field.getSettings().field_mapping.split(',')
        for innervalue in itemvalue or []:
            if fieldtype == 'DOCLINK':
                sub_doc = db.getDocument(innervalue)
                sub_element = dict(serialDoc(fieldsubset=fieldsubset,fieldsremove=fieldsremove,doc=sub_doc))        
            else:
                sub_element = dict([(k, renderSimpleValue(doc,v, grid_form.getFormField(k))) for k,v in zip(grid_field_names, innervalue)]) 
            sub_result.append(sub_element)
        result.append((name, sub_result))
    else:
        renderedValue = renderSimpleValue(doc,itemvalue,field,fieldtype)

        result.append((name, renderedValue))
    return result   

def serialDatagridItem(doc, obj ):
    result = list()
    itemvalue = doc.getItem(obj['name'])
    for el in itemvalue:
        i = 0
        res = dict()
        for fld in obj['field_list']:
            res[fld]= el[i]
            i+=1
        result.append(res)
    return result

def getPlominoValues(doc):
    results = dict(deepcopy(doc.items))
    frm = doc.getForm()
    fieldnames = []
    for i in frm.getFormFields(includesubforms=True, doc=None, applyhidewhen=False):
        if i.getFieldType()=='DATAGRID':
            fieldnames.append(dict(field=i,name=i.getId(),form=i.getSettings().associated_form,field_list=i.getSettings().field_mapping.split(',')))
    try:
        for f in fieldnames:
            if f['name'] in results:
                del results[f['name']]
            results[f['name']]=serialDatagridItem(doc,f)
    except:
        results[f['name']]= []
        #api.portal.show_message(message='Errore nel campo %s' %f['name'], request=doc.REQUEST)
    return json.loads(json.dumps(results, default=DateTime.DateTime.ISO,use_decimal=True ))
