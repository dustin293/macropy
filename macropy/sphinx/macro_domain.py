# -*- coding: utf-8 -*-
# :Project:   macropy3 -- macro domain
# :Created:   ven 13 apr 2018 19:53:42 CEST
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   MIT
# :Copyright: © 2018 Alberto Berti
#


from .domaintools import custom_domain


def setup(app):
    from sphinx.util.docfields import GroupedField
    app.add_domain(custom_domain('MacroPyDomain',
                                 name='macropy',
                                 label='MacroPy',
        elements=dict(
            expr_macro=dict(
                objname='Expression Macro',
                indextemplate='pair: %s; Expression macro',
                #parse=parse_macro,
                fields=[
                    GroupedField('parameter',
                                 label='Parameters',
                                 names=['param'])
                ]
            ),
            block_macro=dict(
                objname='Block Macro',
                indextemplate='pair: %s; Block macro',
                #parse=parse_macro,
                fields=[
                    GroupedField('parameter',
                                 label='Parameters',
                                 names=['param'])
                ]
            ),
            deco_macro=dict(
                objname='Decorator Macro',
                indextemplate='pair: %s; Decorator macro',
                #parse=parse_macro,
                fields=[
                    GroupedField('parameter',
                                 label='Parameters',
                                 names=['param'])
                ]
            ),
        )))
