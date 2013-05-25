import sys
import os
import fnmatch
import plistlib
import shutil
from zipfile import ZipFile as zip
from subprocess import Popen
from PIL import Image, ImageFont, ImageDraw


def chmodeRecursive(rights, path):
    bashCommand = "chmod -R " + rights + " " + path
    print bashCommand
    stream = Popen(bashCommand, shell=True)
    stream.wait()


def extractAll(zipName, path):
    z = zip(zipName)
    for f in z.namelist():
        part_path = path + "/" + f
        if f.endswith('/'):
            print "Make dir: " + part_path
            os.makedirs(part_path)
        else:
            z.extract(f, path)


def locate(pattern, root=os.curdir):
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)


def convertToXML(plist_path, output_path):
    bashCommand = "/usr/bin/plutil -convert xml1 " + plist_path + " -o " + output_path
    print bashCommand
    stream = Popen(bashCommand, shell=True)
    stream.wait()


def uncrushPng(input_path, output_path):
    bashCommand = "/Developer/Platforms/iPhoneOS.platform/Developer/usr/bin/pngcrush -revert-iphone-optimizations -q " + input_path + " " + output_path
    print bashCommand
    stream = Popen(bashCommand, shell=True)
    stream.wait()


def crushPng(input_path, output_path):
    bashCommand = "/Developer/Platforms/iPhoneOS.platform/Developer/usr/bin/pngcrush -iphone -f 0 " + input_path + " " + output_path
    print bashCommand
    stream = Popen(bashCommand, shell=True)
    stream.wait()


def drawTag(tag_text, input_path, output_path):
    # - tag with version
    icon = Image.open(input_path)
    icon_width, icon_height = icon.size

    font_size = int(round(icon_height / 5.7))
    print "Tag font size : %i" % font_size
    font_path = '/Library/Fonts/Arial Bold.ttf'
    font = ImageFont.truetype(font_path, font_size, encoding='unic')

    text_width, text_height = font.getsize(tag_text)
    text_origin = (icon_width - text_width - 5, icon_height - text_height)

    radios = font_size * 2
    ellipse_box = (text_origin[0] - radios * 0.25, text_origin[1], text_origin[0] + radios * 0.75, text_origin[1] + radios)

    rectangle_box = (text_origin[0] + radios * 0.25, text_origin[1], 3000, 3000)

    draw = ImageDraw.Draw(icon)
    draw.ellipse(ellipse_box, fill="#E00000")
    draw.rectangle(rectangle_box, fill="#E00000")
    draw.text(text_origin, tag_text, font=font, fill="#FFFFFF")

    icon.save(output_path)


def zipDirectory(directory, output):
    bashCommand = "zip -qry " + output + " " + directory
    print bashCommand
    stream = Popen(bashCommand, shell=True)
    stream.wait()


def main():

    if len(sys.argv) < 4:
        print "Supply argvs: Archive path (absolute or relative) + Build version + Output ipa name"
        return
    #Extract .ipa files
    archive = sys.argv[1]
    absolute_path = os.path.dirname(os.path.abspath(archive))
    print "Archive path : " + absolute_path

    #Remove previouse .ipa artifacts
    extracted_archive = absolute_path + "/Payload"
    if os.path.exists(extracted_archive):
        shutil.rmtree(extracted_archive)

    extractAll(archive, absolute_path)
    #Mainly for exec file in archive set rights
    chmodeRecursive("777", extracted_archive)

    #.ipad Info plist in binary format, convert to xml one
    plist_binary = locate("Info.plist", extracted_archive).next()
    print "Binary Info.plist path :" + plist_binary
    plist_xml = absolute_path + "/InfoXML.plist"
    convertToXML(plist_binary, plist_xml)
    print "XML Info.plist path :" + plist_xml

    #Parse Info.plist for .app metadata
    plist = plistlib.readPlist(plist_xml)
    bundle_version = plist['CFBundleShortVersionString']
    git_version = sys.argv[2]

    build_version = bundle_version + "." + git_version
    print "Build version : " + build_version

    os.remove(plist_xml)

    #Tag Icon files with version
    for icon_file in plist['CFBundleIcons']['CFBundlePrimaryIcon']['CFBundleIconFiles']:
        print "Tagging : " + icon_file

        # - decompress with pngcrush
        compressed_path = locate(icon_file, extracted_archive).next()
        decompressed_path = absolute_path + "/" + icon_file
        uncrushPng(compressed_path, decompressed_path)

        # - tag with version
        drawTag(build_version, decompressed_path, decompressed_path)

        # - compress with pngcrush
        crushPng(decompressed_path, compressed_path)

        # - remove decompressed image
        os.remove(decompressed_path)

    #Archive .ipa
    ipa_name = sys.argv[3]
    zipDirectory(extracted_archive, absolute_path + "/" + ipa_name)

    shutil.rmtree(extracted_archive)


main()
