if __name__=='__main__':
    new_text = ''
    with open('environment.yaml') as f:
        while True:
            line = f.readline()
            if not line: break
            new_text += line.split('=')[0] +'\n'

    with open('env.yaml', 'w') as f:
        f.write(new_text)