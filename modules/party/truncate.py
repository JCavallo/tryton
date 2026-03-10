from lxml import etree

countries = (
    'address_format_fr',
    'address_format_be',
    'address_format_it',
    'address_format_mc',
    'address_format_es',
    'address_format_ch',
    'address_format_gb',
    'address_format_us',
    )


def truncate_records():
    to_remove = []
    with open('address.xml', 'r') as f:
        tree = etree.parse(f)
    for element in tree.xpath("//record[@model='party.address.format']"):
        if element.attrib['id'] not in countries:
            to_remove.append(element)
    for element in to_remove:
        element.getparent().remove(element)
    with open('address.xml', 'wb') as f:
        f.write(b'<?xml version="1.0"?>\n')
        tree.write(f, pretty_print=True, encoding='utf-8')


if __name__ == '__main__':
    truncate_records()
