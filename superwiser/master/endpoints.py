from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet.protocol import Protocol, Factory

from superwiser.common.jinja_manager import JinjaTemplateManager


class SuperwiserHome(Resource):
    isLeaf = True

    def __init__(self, sauron):
        self.template_manager = JinjaTemplateManager()
        self.sauron = sauron

    def get_process_states(self):
        all_procs = {}
        all_nodes = []

        # Gather all the node details
        nodes = self.sauron.eye.list_nodes()
        for node in nodes:
            all_nodes.append({
                'name': node,
                'node_ip': self.sauron.eye.get_node_details(node)
            })

        # Gather all the process details for each node
        for node in all_nodes:
            procs = self.sauron.eye.list_processes(node['name'])
            for proc in procs:
                num_procs = procs[proc]['numprocs']
                if proc in all_procs:
                    all_procs[proc]['numprocs'] += num_procs
                    all_procs[proc]['nodes'].append(node)
                    continue
                proc_details = {}
                proc_details.update(procs[proc])
                proc_details['name'] = proc
                proc_details['nodes'] = [node]
                all_procs[proc] = proc_details
        return all_procs, all_nodes

    def render_GET(self, request):
        all_procs, all_nodes = self.get_process_states()
        context = {'all_procs': all_procs.values(),
                   'all_nodes': all_nodes}
        return self.template_manager.render_template('index.html',
                                                     context)


class SuperwiserWebFactory(object):
    def make_site(self, sauron):
        root = SuperwiserHome(sauron)
        site = Site(root)
        return site


class SuperwiserTCP(Protocol):
    def parse_command(self, data):
        cmd, args = None, []
        try:
            cmd, rest = data.split('(')
            if cmd in ['increase_procs', 'decrease_procs']:
                prog, factor = rest.split(',')
                prog = prog.strip()
                factor = factor.strip().rstrip(')')
                factor = int(factor)
                args = [prog, factor]
            elif cmd in ['update_conf', 'stop_program',
                         'start_program', 'restart_program']:
                rest = rest.strip().rstrip(')')
                args = [rest]
        except:
            pass

        return (cmd, args)

    def dataReceived(self, data):
        cmd, args = self.parse_command(data)
        if cmd is None:
            self.transport.write('Invalid operation\n')
        elif cmd == 'increase_procs':
            result = self.overlord.increase_procs(*args)
            self.transport.write(str(result) + '\n')
        elif cmd == 'decrease_procs':
            result = self.overlord.decrease_procs(*args)
            self.transport.write(str(result) + '\n')
        elif cmd == 'update_conf':
            conf = requests.get(*args).content
            result = self.overlord.update_conf(conf)
            self.transport.write(str(result) + '\n')
        elif cmd == 'stop_program':
            result = self.overlord.stop_program(*args)
            self.transport.write(str(result) + '\n')
        elif cmd == 'start_program':
            result = self.overlord.start_program(*args)
            self.transport.write(str(result) + '\n')
        elif cmd == 'restart_program':
            result = self.overlord.restart_program(*args)
            self.transport.write(str(result) + '\n')

    def connectionMade(self):
        self.transport.write('Hello\n')

    def connectionLost(self, reason):
        self.transport.write('Goodbye\n')


class SuperwiserTCPFactory(Factory):
    def __init__(self, overlord):
        self.overlord = overlord

    def buildProtocol(self, addr):
        prot = SuperwiserTCP()
        prot.overlord = self.overlord
        return prot
