import pandas as pd
import numpy as np
import os
from sqlalchemy import create_engine
import re
pd.set_option('display.max_rows', 500)

# commande
def select_commande(df) :
    df_commande = df.iloc[:49,:21] # selectionne uniquement les lignes jusque la ligne 50 du csv et 21 premieres colonnes
    df_commande = df_commande[df_commande['Structure'].notna()]
    df_commande = df_commande[df_commande['Type'].notna()]
    df_commande = df_commande[df_commande['Vendeur'].notna()]
    df_commande = df_commande[df_commande['Intitulé'].notna()]
    df_commande = df_commande[df_commande['Transaction'].notna()]
    df_commande = df_commande[df_commande['Moyen de paiement'].notna()]
    df_commande = df_commande[df_commande['Déplacement'].notna()]
    df_commande = df_commande[df_commande['Quantité'].notna()]
    df_commande = df_commande[df_commande['Reduction'].notna()]
    df_commande = df_commande[df_commande["Date d'achat"].notna()]  ######/!\/!\ OCTOBRE PROBLEME DATE D'ACHAT  NAN A REPARER PLUS TARD /!\ /!\ #####

    #on selectionne les colonnes utiles pour nous par leur nom dans le DF    df_commande = df_commande.rename(columns={'Structure': 'type_structure_nom', 'Transaction': 'type_transaction_nom', 'Moyen de paiement':'moyen_paiement_nom', "Nom":'client_nom', "Prénom":'client_prenom',"Date d'achat":'commande_date_achat'})
    df_commande = df_commande[['Date soin', 'Nom' ,'Prénom', 'Type', 'Vendeur', 'Intitulé','Déplacement', 'Quantité',
                               'Reduction', "Date d'achat", 'Date Encaissement ', 'Date perception', 'Date remboursement']]
    
    #on change nom col pour correspondre au nom dans les tables type_structure, type_transaction, moyen_paiement et commande (pour commande_date_achat et client_id)
    df_commande = df_commande.rename(columns={'Date soin': 'commande_date_soin', 'Nom': 'client_nom',
                                              'Prénom': 'client_prenom', 'Type': 'type_activite_nom', 'Vendeur': 'vendeur_nom',
                                              'Intitulé': 'activite_nom', 'Déplacement': 'commande_deplacement',
                                              'Quantité': 'commande_quantité', 'Reduction': 'commande_reduction',
                                              "Date d'achat": 'commande_date_achat', 'Date Encaissement ': 'commande_date_encaissement',
                                              'Date perception': 'commande_date_perception', 'Date remboursement': 'commande_date_remboursement'})
    return df_commande

def equal_or_both_null(s1, s2) :
    s1_2=str(s1)
    s2_2=str(s2)
    if pd.isnull(s1_2) & pd.isnull(s2_2) :
        return True
    if pd.isnull(s1_2) | pd.isnull(s2_2) :
        return False
    if s1_2.lower() == s2_2.lower() :
        return True
    return False

#transforme les dates format excel au format SQL et si Nan retourne Nan
def excel_to_sql_date(date):
    if pd.isnull(date):
        return date
    else:
        date=re.sub(r"/","-",date) #on transforme les "/" en "-"
        date=re.sub(r"(\d\d)-(\d\d)-(\d{4})",r"\3-\2-\1",date) #on inverse les jours et les mois
        return date

# remplace les colonnes client_nom et client_prenom par client_id
def get_client_id(df_commande, connection) :
    pd.options.mode.chained_assignment = None
    df_res=df_commande
    df_from_db = pd.read_sql_query('SELECT client_id, client_nom, client_prenom FROM client', connection)
    df_res["client_id"]=np.nan
    def same_line(i, j, dfcom, dfdb) :
        nom = str(dfcom.loc[i,"client_nom"]).lower()
        nom_db = str(dfdb.loc[j,"client_nom"]).lower()
        prenom = str(dfcom.loc[i,"client_prenom"]).lower()
        prenom_db = str(dfdb.loc[j,"client_prenom"]).lower()
        if ( (equal_or_both_null(nom,nom_db)) & (equal_or_both_null(prenom,prenom_db)) ) :
            return True
        return False
    for i in df_res.index :
        for j in df_from_db.index :
            if same_line(i, j, df_res, df_from_db) :
                df_res.loc[i, "client_id"]=df_from_db.loc[j, "client_id"] # quand un couple nom/prenom est trouve dans la bdd, son id lui est associe
    pd.options.mode.chained_assignment = "warn"
    df_res=df_res.drop(["client_nom", "client_prenom"], axis=1)
    return df_res

# ajoute l'id de la commande a partir de l'id client et de la date d'achat de la commande
def get_commande_id(df_commande, connection) :
    df_res=df_commande
    df_from_db = pd.read_sql_query('SELECT commande_id, commande_date_achat, client_id, moyen_paiement_id, type_transaction_id, type_structure_id FROM commande', connection)
    df_res["commande_id"]=np.nan
    def same_line(i, j, dfcom, dfdb) :
        c = str(dfcom.loc[i,"commande_date_achat"])
        c_db = str(dfdb.loc[j,"commande_date_achat"])
        cli = float(dfcom.loc[i,"client_id"])
        cli_db = float(dfdb.loc[j,"client_id"])
        if ( (c==c_db) & (cli==cli_db) ) :
            return True
        return False
    for i in df_res.index :
        for j in df_from_db.index :
            if same_line(i, j, df_res, df_from_db) :
                df_res.loc[i, "commande_id"] = df_from_db.loc[j, "commande_id"]
    df_res=df_res.drop(["client_id"], axis=1)
    return df_res

# remplace le nom du vendeur par son id associe
def get_vendeur_id(df_commande, connection) :
    df_res=df_commande
    df_from_db = pd.read_sql_query('SELECT vendeur_id, vendeur_nom FROM vendeur', connection)
    df_res["vendeur_id"]=np.nan
    for i in df_res.index :
        for j in df_from_db.index :
            if(equal_or_both_null(df_res.loc[i, "vendeur_nom"].lower(), df_from_db.loc[j, "vendeur_nom"].lower())) :
                df_res.loc[i, "vendeur_id"]=df_from_db.loc[j, "vendeur_id"] # quand un couple nom/prenom est trouve dans la bdd, son id lui est associe
    pd.options.mode.chained_assignment = "warn"
    df_res=df_res.drop(["vendeur_nom"], axis=1)
    return df_res

# remplace les colonnes type_activite_nom et activite_nom par l'id associe
def get_type_activite_id(df_commande, connection) :
    pd.options.mode.chained_assignment = None
    df_res=df_commande
    df_from_db = pd.read_sql_query('SELECT type_activite_id, type_activite_nom, activite_nom FROM type_activite', connection)
    df_res["type_activite_id"]=np.nan
    def same_line(i, j, dfcom, dfdb) :
        type_a_nom = str(dfcom.loc[i,"type_activite_nom"]).lower()
        type_a_nom_db = str(dfdb.loc[j,"type_activite_nom"]).lower()
        a_nom = str(dfcom.loc[i,"activite_nom"]).lower()
        a_nom_db = str(dfdb.loc[j,"activite_nom"]).lower()
        if (type_a_nom==type_a_nom_db) & (a_nom==a_nom_db) :
            return True
        return False
    for i in df_res.index :
        for j in df_from_db.index :
            if same_line(i, j, df_res, df_from_db) :
                df_res.loc[i, "type_activite_id"] = df_from_db.loc[j, "type_activite_id"]
    pd.options.mode.chained_assignment = "warn"
    df_res=df_res.drop(["type_activite_nom", "activite_nom"], axis=1)
    return df_res

# recupere l'id de l'activite a partir de l'id du type d'activite, de l'id du vendeur et de la date d'achat (mois et annee) 
def get_activite(df_commande, connection) :
    pd.options.mode.chained_assignment = None
    df_res=df_commande
    df_from_db = pd.read_sql_query('SELECT activite_id, activite_mois, type_activite_id, vendeur_id FROM activite', connection)
    df_res["activite_id"]=np.nan
    def same_line(i, j, dfcom, dfdb) :
        type_a_id = float(dfcom.loc[i,"type_activite_id"])
        type_a_id_db = float(dfdb.loc[j,"type_activite_id"])
        vendeur_id = float(dfcom.loc[i,"vendeur_id"])
        vendeur_id_db = float(dfdb.loc[j,"vendeur_id"])
        mois_annee = str(dfcom.loc[i,"commande_date_achat"])
        mois=mois_annee[5:7]
        annee=mois_annee[0:4]
        mois_annee_db = str(dfdb.loc[j, "activite_mois"])
        mois_db=mois_annee_db[5:7]
        annee_db=mois_annee_db[0:4]
        if (type_a_id==type_a_id_db) & (vendeur_id==vendeur_id_db) & (mois==mois_db) & (annee==annee_db):
            return True
        return False
    for i in df_res.index :
        for j in df_from_db.index :
            if same_line(i, j, df_res, df_from_db) :
                df_res.loc[i, "activite_id"] = df_from_db.loc[j, "activite_id"]
    pd.options.mode.chained_assignment = "warn"
    df_res=df_res.drop(["type_activite_id", "vendeur_id", "commande_date_achat"], axis=1)
    return df_res

#Main
conn=create_engine('mysql+mysqlconnector://root:root@localhost:3306/eviesens')

filepaths=os.listdir("./donnees/fiches_mensuelles/") #récupère liste des noms des fichiers dans le dossier "fiches_mensuelles"

for i in range(len(filepaths)) :
    filepaths[i]="./donnees/fiches_mensuelles/"+filepaths[i] #on récupère liste des filepath de chaque fiche mensuelle

for filepath in filepaths :
    print(filepath)
    df=pd.read_csv(filepath)
    df_commande=select_commande(df)
    df_commande['commande_date_soin'] = df_commande['commande_date_soin'].transform(lambda x: excel_to_sql_date(x))
    df_commande['commande_date_achat'] = df_commande['commande_date_achat'].transform(lambda x: excel_to_sql_date(x))
    df_commande['commande_date_encaissement'] = df_commande['commande_date_encaissement'].transform(lambda x: excel_to_sql_date(x))
    df_commande['commande_date_perception'] = df_commande['commande_date_perception'].transform(lambda x: excel_to_sql_date(x))
    df_commande['commande_date_remboursement'] = df_commande['commande_date_remboursement'].transform(lambda x: excel_to_sql_date(x))

    df_commande=get_client_id(df_commande, conn)
    df_commande=get_commande_id(df_commande, conn)

    df_commande=get_vendeur_id(df_commande, conn)
    df_commande=get_type_activite_id(df_commande, conn)
    df_commande=get_activite(df_commande, conn)

    df_commande = df_commande[df_commande["activite_id"].notna()]  ######/!\/!\ PROBLEME L5 SEPTEMBRE : ACTIVITE ID INEXISTANT(ligne effacee) a corriger /!\ /!\ #####
    print(df_commande)
    # TODO : couple activite_id/commande_id dupliquee : (triplet id_cli, date d'achat pour la cle commande et activite_id) (JUIN)
    df_commande.to_sql("commande_activite", con=conn, index=False, if_exists='append')
