# -*- mode: ruby -*-

Vagrant.configure(2) do |config|
  config.vm.box = 'trusty64'

  config.vm.network 'forwarded_port', guest: 5000, host: 5000

  config.vm.provision 'ansible' do |ansible|
    ansible.playbook = 'deploy/playbook-dev.yml'
    ansible.vault_password_file = '~/.config/ansible/vault-password'
  end
end
