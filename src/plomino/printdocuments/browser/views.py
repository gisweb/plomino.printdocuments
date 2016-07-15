# -*- coding: utf-8 -*-
from Products.Five import BrowserView
from urlparse import urlparse, parse_qs
from zope.interface import implements
from zope.component import getMultiAdapter
from Acquisition import aq_inner
from ..serialdoc import serialDoc,serialItem,serializeGrid,convertToPdf,is_json,getServiceConfiguration
from plone.app.contenttypes.interfaces import IFile


from plomino.printdocuments import _

import base64
import json
import logging
import requests

_logger = logging.getLogger('plomino.printdocuments')

class printService(BrowserView):

    result = {'success': 0}
    printConfig = None

    def __init__(self, context, request):

        self.context = context
        self.request = request
        self.doc = context
        self.print_form = request.get('form') or False
        self.toPdf = request.get('pdf') or False
        self.field = request.get('field') or False

        #URL del servizio di creazione del documento
        db = context.getParentDatabase()
        if "config_printdocuments" in db.resources.keys():
            self.printConfig = db.resources.config_printdocuments()

    def serializeDocument(self):
        """
        BW CON LA SERIALIZZAZIONE DEL DOCUMENTO
        PARAMETRI DI REQUEST
        formid: form da usare per serializzare il documento se non viene passato usa il form del plomino document
        rendered: decodifica le chiavi in valori (etichiette) 
        follow_doclink: include la serializzazione dei docuemnti figli (TO DO DA VEDERE)
        """  

        render = self.request.get('render', False)
        if render:
            render = True
        follow_doclink = self.request.get('follow_doclink', False)
        if follow_doclink:
            follow_doclink = True

        formid = self.request.get('formid','')


        #serializzo il documento
        serializedDoc = serialDoc(doc=self.doc, formid=formid, render=render, follow_doclink=follow_doclink)
        if not serializedDoc:
            self.result['msg'] = "Errore nella serializzazione del documento"
            return self.render() 
        
        self.request.response.setHeader("Content-type", "application/json")
        return json.dumps(serializedDoc)


    def printDocument(self): 
        """
        GENERAZIONE DI UN DOCX PARTENDO DA UN MODELLO DI STAMPA 
        <docurl>/@@printdoc?app=praticaweb&model=relazione_asseverata_scia&grp=relazioni&form=scia-completa&field=campo&pdf=1&jsondump=1
        PARAMETRI DI REQUEST
        model:modello di stampa da usare
        grp:sottocartella del modello di stampa
        app:applicazione
        form:(consigliato)form da usare per serializzare il documento se non viene passato usa il form del plomino document
        field:(facoltativo) se viene passato setta l'item sul plomino document
        pdf:(facoltativo) se vine passato cre anche il file pdf
        jsondump:(per debug) esce restituendo il documento serializzato
        """  
        request = self.request
        if not self.print_form:
            self.print_form = self.doc.Form

        app = request.get('app')  #praticaweb, dehors, trasporti..
        grp = request.get('grp')  #autorizzazione....
        model = request.get('model')  #nome del modello

        redirect_url = ''
        fieldsubset = '' 
        fieldsremove = ''

        if not self.printConfig:
            self.result['msg'] = "MANCA IL FILE DI CONFIGURAZIONE resources/config_printdocuments"
            return self.render()

        if not self.doc.isCurrentUserAuthor(self.doc):
            self.result['msg'] = "ACCESSO NON CONSENTITO"
            return self.render()

        if not "ws_createdocx" in self.printConfig:
            self.result['msg'] = "ws_createdocx non assegnato"
            return self.render()
        serviceUrl = self.printConfig["ws_createdocx"]

        if not "models_folder" in self.printConfig:
            self.result['msg'] = "models_folder non assegnato"
            return self.render()
        models = self.printConfig['models_folder']    

        portal = self.doc.portal_url.getPortalObject()
        if not models in portal.keys():
            self.result['msg'] = "Non esiste la cartella %s" %(models)
            return self.render()

        modelsFolder = portal[models]
        if not app in modelsFolder.keys():
            self.result['msg'] = "Non esiste la cartella %s/%s" %(models,app)
            return self.render()

        modelsFolder = portal[models][app]
        if not grp in modelsFolder.keys():
            self.result['msg'] = "Non esiste la cartella %s/%s/%s" %(models,app,grp)
            return self.render()   
    
        modelsFolder = portal[models][app][grp]
        if not model in modelsFolder.keys():
            self.result['msg'] = "Non esiste il file %s/%s/%s/%s" %(models,app,grp,model)
            return self.render()

        #serializzo il documento
        serializedDoc = serialDoc(self.doc,self.print_form)
        if not serializedDoc:
            self.result['msg'] = "Errore nella serializzazione del documento"
            return self.render() 

        """
        SERIALIZZO I DATI DI UNA RIGA DI DATAGRID
        AGGIUNGO/SOSTITUISCO NEL DOCUMENTO SERIALIZZATO I CAMPI PRESENTI IN UNA RIGA DI UN DATAGRID
        Caso d'uso: Stampo 1 documento per ogni soggetto presente in un datagrid. 
        grid: nome del campo con il datagrid
        grid_index: riga da da accodare serializzata
        """
        grid = request.get('grid')
        grid_index = request.get('grid_index')
        if grid and grid_index:
            rows = serializedDoc[grid]
            grid_index = int(grid_index)
            if rows and len(rows) > grid_index:
                row = rows[grid_index]
                serializedDoc.update(row)
   
        #passando in request il parametro testjson visualizza la json del documento serializzato
        if request.get('jsondump')=='1':
            self.request.response.setHeader("Content-type", "application/json")
            return json.dumps(serializedDoc)


        #Stampa da modello
        modelFile = modelsFolder[model]
        
        if IFile.providedBy(modelFile):
            modelContent = base64.b64encode(modelFile.file.data)
            modelName = modelFile.file.filename
            modelMimeType = modelFile.file.contentType
        else:
            modelContent = base64.b64encode(modelFile.get_data())
            #estensione dei file per stampe
            modelName = modelFile.getFilename()
            modelMimeType = modelFile.getContentType()
            modelIcon = modelFile.getIcon()

        #Parametri della chiamata al servizio di creazione
        data = dict(
            model = modelContent,
            dataType = 'JSON',
            data = json.dumps(serializedDoc)
        )
        if self.toPdf:
            data["pdf"] = 1
        #Creazione del documento tramite webservice
        #plone_tools = getToolByName(self.doc.getParentDatabase().aq_inner, 'plone_utils')
        #plone_tools.addPortalMessage(json.dumps(query), 'message')
        #import pdb;pdb.set_trace()

        try:
            #TODO CONTROLLO ERRORI
            wsres = requests.post(serviceUrl, data)
            res = wsres.json()

        except Exception as error:    
            msg = ('%s: %s' % (type(error), error), 'error')
            #plone_tools.addPortalMessage(*msg, request=self.doc.REQUEST)
            #self.doc.REQUEST.RESPONSE.redirect(self.doc.absolute_url())
            self.result['msg'] = msg
            self.result['response'] = wsres
            return self.render() 
        
        content = ''
        pdfContent = ''
        if res['success'] == 1:
            if "content" in res:
                content = base64.b64decode(res['content'])
            if "pdfContent" in res:
                pdfContent = base64.b64decode(res['pdfContent'])   

            return self.renderContent(modelName,content,modelMimeType,pdfContent)

        else:
            self.result['msg'] = "Errore nella creazione del documento"
            return self.render() 


    def convertToPdf(self, filename):
        #TODO GESTIONE ERRORI
        #URL del servizio di Conversione
        #????????????DA RIVEDERE???????????
        if not "ws_convertpdf" in self.printConfig:
            self.result['msg'] = "ws_convertpdf non assegnato"
            return self.render()
        serviceUrl = self.printConfig["ws_convertpdf"]
        newfilename = filename.replace('.docx','.pdf').replace('.odt','.pdf')
        query = dict(
            docurl = '%s/%s' %(self.doc.absolute_url(),filename)
            )
        try:
            r = requests_post(serviceUrl, query, 'json', timeout=30)
        except Exception as error:
            msg = ('%s: %s' % (type(error), error), 'error')
            return msg
        else:
            return r['text']
            result = r['text']
            if is_json(result):
                res = json.loads(result)
                return res


    def docx2pdf(self):
        #?????????????da rivedere
        convertToPdf(self.doc)


    def form2Pdf(self):
        """
        WRAP PER WKPDF
        crea il documento pdf usando la form che viene passata
        se non viene passata la form usa la form corrente del documento
        PARAMETRI DI REQUEST
        form:(consigliato)form da usare per serializzare il documento se non viene passato usa il form del plomino document
        field:(facoltativo) se viene passato setta l'item sul plomino document

        """
        #import pdb;pdb.set_trace()
        view = getMultiAdapter((self.doc, self.request), name='wkpdf')
        try:
            pdfContent = view.get_pdf_file()
        except:
            pass

        filename = self.request.get("filename") or self.field or "allegato"
        filename = filename + '.pdf'

        self.toPdf = True
        return self.renderContent(filename,'','',pdfContent)

    def renderContent(self,filename,content,contentMimeType,pdfContent):
        """
        SE PASSO IL PARAMETRO FIELD IN REQUEST METTO IL DOCUMENTO CREATO NEL FIELD DI ATTACHMENT
        ALTRIMENTI SCARICO DIRETTAMENTE IL FILE
        """
        #import pdb;pdb.set_trace()

        pdfName = filename.replace('.docx','.pdf').replace('.odt','.pdf')

        if self.field:
            if content:
                #self.doc.removeItem(self.field)
                (ff,cc) = self.doc.setfile(content, filename=filename, overwrite=True, contenttype=contentMimeType)
                if ff and cc:
                    self.doc.setItem(self.field, {ff: cc})
                    self.result['success'] = 1
                    self.result['field'] = self.field
                    self.result['fileName'] = filename

            if self.toPdf and pdfContent:
                (ff,cc) = self.doc.setfile(pdfContent, filename=pdfName, overwrite=True, contenttype='application/pdf')
                if ff and cc:
                    #SE GENERO IL PDF NON AGGIUNGO MA SOSTITUISCO NELL ITEM IL PDF AD DOCX PUR MANTENENDO IL DOCX ALLEGATO
                    #files = self.doc.getItem(self.field)
                    #files[ff] = cc
                    #self.doc.setItem(self.field, files)
                    self.doc.setItem(self.field, {ff: cc})
                    self.result['success'] = 1
                    self.result['field'] = self.field
                    self.result['pdfName'] = pdfName

            return self.render() 

        else:
            if self.toPdf: # se richiedo il pdf esco con solo il pdf
                contentMimeType = 'application/pdf'
                filename = pdfName
                content = pdfContent

            self.request.RESPONSE.setHeader('content-type', contentMimeType)
            self.request.RESPONSE.setHeader("Content-Disposition", "inline; filename=" + filename)
            return content

    def render(self):
        self.request.response.setHeader("Content-type", "application/json")
        return json.dumps(self.result)
