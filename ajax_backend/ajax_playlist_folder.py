

from init import app
from utils import getDefaultJSON
from utils.jsontools import makeResponseSuccess, makeResponseError
from utils.interceptors import loginOptional, jsonRequest, loginRequiredJSON

from services.playlistFolder import *

@app.route('/folder/create', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_folder_create(rd, data, user) :
    privateView = getDefaultJSON(data, 'privateView', False)
    privateEdit = getDefaultJSON(data, 'privateEdit', True)
    createFolder(user, data.root, data.name, privateView, privateEdit)

@app.route('/folder/delete', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_folder_delete(rd, data, user) :
    deleteFolder(user, data.path)

@app.route('/folder/delete_many', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_folder_delete_many(rd, data, user) :
    deleteFolders(user, data.paths)

@app.route('/folder/rename', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_folder_rename(rd, data, user) :
    renameFolder(user, data.path, data.new_name)

@app.route('/folder/change_access', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_folder_change_access(rd, data, user) :
    changeFolderAccess(user, data.path, data.private_view, data.private_edit)

@app.route('/folder/add_pid', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_folder_add_pid(rd, data, user) :
    addPlaylistsToFolder(user, data.path, data.pids)

@app.route('/folder/del_pid', methods = ['POST'])
@loginRequiredJSON
@jsonRequest
def ajax_folder_del_pid(rd, data, user) :
    removePlaylistsFromFolder(user, data.path, data.pids)

@app.route('/folder/view', methods = ['POST'])
@loginOptional
@jsonRequest
def ajax_folder_view(rd, data, user) :
    if user is None :
        return "json", makeResponseSuccess(listFolder(user, data.uid, data.path))
    else :
        if hasattr(data, 'uid') :
            uid = data.uid
        else :
            uid = user['_id']
        return "json", makeResponseSuccess(listFolder(user, uid, data.path))

